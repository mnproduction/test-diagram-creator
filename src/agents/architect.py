# src/agents/architect.py

import asyncio
import os
import re

import structlog
from pydantic_ai import Agent

from .agent_settings import (
    ARCHITECT_ANALYSIS_PROMPT,
    ARCHITECT_FORMATTER_PROMPT,
    ARCHITECT_SYSTEM_PROMPT,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    MAX_RETRIES_SINGLE_MODEL,
    RETRY_BACKOFF_BASE,
)
from .base import (
    ComponentAnalysis,
    ComponentType,
    ExecutionPlan,
    ServiceComponent,
    ToolCall,
)

logger = structlog.get_logger(__name__)


class ArchitectAgent:
    """
    Enhanced Architect Agent using a two-stage LLM pipeline for robust analysis.
    1. Analysis Stage: LLM generates a structured Markdown analysis.
    2. Formatting Stage: A second LLM call converts the Markdown to strict JSON.
    """

    def __init__(self):
        self.agent_id = "architect"

        # Require at least Gemini API key
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Configure the Gemini model for PydanticAI
        os.environ["GEMINI_API_KEY"] = self.gemini_api_key
        self.gemini_model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

        # Initialize fallback LLM model - OpenRouter via PydanticAI
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)

        # Require at least one API key
        if not self.gemini_api_key and not self.openrouter_api_key:
            raise ValueError(
                "Either GEMINI_API_KEY or OPENROUTER_API_KEY environment variable is required"
            )

        # Initialize agents for available models
        self.agents = {}

        if self.gemini_api_key:
            # Configure the Gemini model for PydanticAI
            os.environ["GEMINI_API_KEY"] = self.gemini_api_key
            self.agents["gemini"] = Agent(
                model=self.gemini_model,
                system_prompt=ARCHITECT_SYSTEM_PROMPT,
                output_type=ComponentAnalysis,
            )
            logger.info(
                "Initialized Gemini agent for primary LLM analysis",
                model=self.gemini_model,
            )

        if self.openrouter_api_key:
            # Configure OpenRouter model for PydanticAI
            os.environ["OPENROUTER_API_KEY"] = self.openrouter_api_key
            self.agents["openrouter"] = Agent(
                model=f"openrouter:{self.openrouter_model}",
                system_prompt=ARCHITECT_SYSTEM_PROMPT,
                output_type=ComponentAnalysis,
            )
            logger.info(
                "Initialized OpenRouter agent for fallback LLM analysis",
                model=self.openrouter_model,
            )

        # Determine model priority order
        self.model_priority = []
        if "gemini" in self.agents:
            self.model_priority.append("gemini")
        if "openrouter" in self.agents:
            self.model_priority.append("openrouter")

        logger.info("LLM model priority", priority=" -> ".join(self.model_priority))

        # Agent for Stage 1: Text-based analysis (returns Markdown string)
        self.analysis_agent = Agent(
            model=self.gemini_model,
            system_prompt=ARCHITECT_SYSTEM_PROMPT,
            output_type=str,  # Expecting a Markdown string
        )

        # Agent for Stage 2: JSON formatting (returns ComponentAnalysis)
        self.formatter_agent = Agent(
            model=self.gemini_model,
            system_prompt="You are a precise text-to-JSON formatting utility.",
            output_type=ComponentAnalysis,  # Expecting the final Pydantic model
        )

        logger.info(
            "Initialized ArchitectAgent with two-stage LLM pipeline",
            model=self.gemini_model,
        )

    async def _analyze_infrastructure(self, description: str) -> ComponentAnalysis:
        """
        Executes the two-stage pipeline: Analyze to Markdown, then Format to JSON.
        This approach is dramatically more robust than single-stage complex prompts.
        """
        logger.info("Stage 1: Performing Markdown analysis...")
        analysis_prompt = ARCHITECT_ANALYSIS_PROMPT.format(description=description)

        logger.debug("Executing Stage 1: Analysis", prompt=analysis_prompt)

        last_error = None
        for attempt in range(MAX_RETRIES_SINGLE_MODEL):
            try:
                # === STAGE 1: Get Markdown Analysis ===
                logger.debug(
                    "Analysis attempt",
                    attempt=attempt + 1,
                    max_retries=MAX_RETRIES_SINGLE_MODEL,
                )
                markdown_analysis_result = await self.analysis_agent.run(
                    analysis_prompt
                )
                markdown_analysis = markdown_analysis_result.output

                logger.debug(
                    "Stage 1 LLM response received", response=markdown_analysis
                )

                if not markdown_analysis or "Components" not in markdown_analysis:
                    raise ValueError("LLM failed to generate a valid Markdown analysis")

                # === STAGE 2: Format Markdown to JSON ===
                logger.info("Stage 2: Formatting Markdown to JSON...")
                formatter_prompt = ARCHITECT_FORMATTER_PROMPT.format(
                    markdown_analysis=markdown_analysis
                )

                logger.debug("Executing Stage 2: Formatting", prompt=formatter_prompt)

                final_result = await self.formatter_agent.run(formatter_prompt)
                analysis_obj = final_result.output

                logger.debug(
                    "Stage 2 LLM response received", response=analysis_obj.model_dump()
                )

                if not analysis_obj.services:
                    raise ValueError(
                        "LLM formatting resulted in an empty services list"
                    )

                logger.info(
                    "Two-stage analysis successful",
                    num_services=len(analysis_obj.services),
                    num_clusters=len(analysis_obj.clusters),
                    confidence=analysis_obj.confidence_score,
                )

                # Debug logging to see what LLM generated
                logger.debug("LLM Analysis Details", analysis=analysis_obj.model_dump())

                # Add model info for transparency
                analysis_obj.errors.append(
                    f"Analysis provided by: Gemini two-stage pipeline ({self.gemini_model})"
                )

                return analysis_obj

            except Exception as e:
                logger.error(
                    "Two-stage analysis failed",
                    attempt=attempt + 1,
                    max_retries=MAX_RETRIES_SINGLE_MODEL,
                    error=str(e),
                )
                last_error = e

                if attempt < MAX_RETRIES_SINGLE_MODEL - 1:
                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(RETRY_BACKOFF_BASE**attempt)

        # All attempts failed - return emergency fallback
        logger.error(
            "🚨 All two-stage LLM attempts failed. Triggering emergency fallback."
        )
        return ComponentAnalysis(
            services=[
                ServiceComponent(
                    name="error_node",
                    service_name="LLM Analysis Failed",
                    component_type=ComponentType.AWS_COMPUTE,
                )
            ],
            clusters=[],
            connections=[],
            confidence_score=0.0,
            errors=[
                f"All two-stage LLM analysis attempts failed. Last error: {str(last_error)}"
            ],
        )

    def _get_aws_tool_for_service(self, service: ServiceComponent) -> tuple[str, dict]:
        """
        Intelligent service mapping that uses both component type and service name for optimal icons.
        """
        # Intelligent name-based service mapping for better visual representation
        name_lower = f"{service.name.lower()} {service.service_name.lower()}"

        # Primary mapping based on service name/function
        if any(
            keyword in name_lower for keyword in ["github", "git", "repo", "source"]
        ):
            aws_service_type = "codecommit"  # Git-like service
        elif any(
            keyword in name_lower for keyword in ["jenkins", "ci", "build", "pipeline"]
        ):
            aws_service_type = "codebuild"  # CI/CD service
        elif any(
            keyword in name_lower
            for keyword in ["slack", "notification", "alert", "message"]
        ):
            aws_service_type = "sns"  # Messaging/notification service
        elif any(keyword in name_lower for keyword in ["kubernetes", "k8s", "cluster"]):
            aws_service_type = "eks"  # Kubernetes service
        elif any(
            keyword in name_lower for keyword in ["pod", "container", "api_server"]
        ):
            aws_service_type = "ecs"  # Container service for pods
        elif any(
            keyword in name_lower
            for keyword in ["database", "db", "rds", "mysql", "postgres"]
        ):
            aws_service_type = "rds"
        elif any(keyword in name_lower for keyword in ["queue", "sqs", "message"]):
            aws_service_type = "sqs"
        elif any(
            keyword in name_lower for keyword in ["lambda", "function", "serverless"]
        ):
            aws_service_type = "lambda"
        elif any(
            keyword in name_lower
            for keyword in ["load_balancer", "alb", "elb", "loadbalancer"]
        ):
            aws_service_type = "elb"
        elif any(
            keyword in name_lower
            for keyword in ["api_gateway", "apigateway", "gateway"]
        ):
            aws_service_type = "apigateway"
        elif any(keyword in name_lower for keyword in ["s3", "storage", "bucket"]):
            aws_service_type = "s3"
        elif any(
            keyword in name_lower for keyword in ["monitor", "cloudwatch", "logging"]
        ):
            aws_service_type = "cloudwatch"
        else:
            # Fallback to component type mapping
            component_type_str = (
                service.component_type.value
                if hasattr(service.component_type, "value")
                else str(service.component_type)
            )
            service_icon_map = {
                "aws_compute": "ec2",
                "aws_database": "rds",
                "aws_network": "elb",
                "aws_storage": "s3",
                "ec2": "ec2",
                "lambda": "lambda",
                "ecs": "ecs",
                "rds": "rds",
                "dynamodb": "dynamodb",
                "redshift": "redshift",
                "alb": "elb",
                "apigateway": "apigateway",
                "s3": "s3",
                "sqs": "sqs",
                "kinesis": "kinesis",
                "cloudwatch": "cloudwatch",
                "onprem": "ec2",
                "kubernetes": "eks",
                "generic": "ec2",  # Default fallback
            }
            aws_service_type = service_icon_map.get(component_type_str.lower(), "ec2")

        # This was incorrectly flagged by the linter but is needed by the caller.
        params = {"label": service.service_name.title()}

        logger.info(
            f"🔍 SMART MAPPING: '{service.service_name}' ({service.name}) -> AWS icon '{aws_service_type}'"
        )
        return "create_aws_node", {"aws_service": aws_service_type, **params}

    def _extract_diagram_title(self, description: str) -> str:
        """Extracts a user-specified title from the description."""
        # Regex to find titles in quotes or with specific keywords
        patterns = [
            r"titled \"([^\"]+)\"",  # "titled "..."
            r"title(?: is)? '([^']+)'",  # "title is '...'"
            r"for a '([^']+)' system",  # "for a '...' system"
            r"named \"([^\"]+)\"",  # "named "..."
        ]
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)

        # Fallback to a generic title if no specific title is found
        return "System Architecture"

    def generate_execution_plan(
        self, analysis: ComponentAnalysis, description: str
    ) -> ExecutionPlan:
        """
        Generates the final execution plan. Much simpler now since LLM handles the complex logic.
        """
        logger.info("=" * 80)
        logger.info("🔍 VERBOSE DEBUG: EXECUTION PLAN GENERATION")
        logger.info("=" * 80)
        logger.info("INPUT ANALYSIS:")
        logger.info(f"  Services count: {len(analysis.services)}")
        for service in analysis.services:
            logger.info(
                f"    - {service.name} ({service.service_name}) [{service.component_type}]"
            )
        logger.info(f"  Clusters count: {len(analysis.clusters)}")
        for cluster in analysis.clusters:
            logger.info(
                f"    - {cluster.name} ({cluster.label}) contains: {cluster.services}"
            )
        logger.info(f"  Connections count: {len(analysis.connections)}")
        for conn in analysis.connections:
            logger.info(f"    - {conn.source} -> {conn.target}")
        logger.info("=" * 80)

        tool_sequence: list[ToolCall] = []
        order = 0

        # Extract dynamic title from prompt
        title = self._extract_diagram_title(description)
        logger.info(f"🔍 EXTRACTED TITLE: '{title}'")

        # Default graph attributes for a polished look
        default_graph_attr = {
            "rankdir": "LR",
            "splines": "ortho",
            "nodesep": "1.8",
            "ranksep": "3.0",
            "compound": "true",
            "bgcolor": "#f8f9fa",
            "fontname": "Arial",
            "fontsize": "14",
            "fontcolor": "#2c3e50",
            "pad": "1.2",
            "dpi": "150",
        }

        # Initialize diagram
        tool_sequence.append(
            ToolCall(
                tool_name="initialize_diagram",
                parameters={"title": title, "graph_attr": default_graph_attr},
                execution_order=order,
            )
        )
        order += 1

        logger.info("🔍 CREATING CLUSTERS:")

        # Sort clusters to ensure parents are created before children
        sorted_clusters = []
        clusters_to_process = analysis.clusters[:]
        added_in_pass = -1

        while clusters_to_process and added_in_pass != 0:
            added_in_pass = 0
            remaining_clusters = []
            for cluster in clusters_to_process:
                # A cluster can be added if it has no parent, or its parent is already added
                if cluster.parent is None or cluster.parent in {
                    c.name for c in sorted_clusters
                }:
                    sorted_clusters.append(cluster)
                    added_in_pass += 1
                else:
                    remaining_clusters.append(cluster)
            clusters_to_process = remaining_clusters

        if clusters_to_process:
            logger.error(
                f"🚨 Could not resolve cluster hierarchy. Orphaned clusters: {[c.name for c in clusters_to_process]}"
            )
            # Add error to analysis object if possible or handle appropriately

        # Create cluster tool calls from the sorted list
        for cluster in sorted_clusters:
            cluster_graph_attr = {
                "style": "rounded,filled",
                "fillcolor": "#e3f2fd",
                "color": "#1976d2",
                "penwidth": "2",
                "fontname": "Arial Bold",
                "fontsize": "16",
                "fontcolor": "#1976d2",
                "margin": "30",
                "pad": "0.8",
                "rank": "same",
            }
            tool_sequence.append(
                ToolCall(
                    tool_name="create_cluster",
                    parameters={
                        "name": cluster.name,
                        "label": cluster.label,
                        "parent_name": cluster.parent,  # Pass parent info to tool
                        "graph_attr": cluster_graph_attr,
                    },
                    execution_order=order,
                )
            )
            order += 1
            logger.info(
                f"🔍 TOOL {order}: create_cluster - {cluster.name} (Parent: {cluster.parent or 'None'})"
            )

        logger.info("🔍 CREATING SERVICE NODES:")
        # Create a map of which services are in which immediate cluster
        service_to_cluster_map = {}
        for cluster in analysis.clusters:
            for service_name in cluster.services:
                service_to_cluster_map[service_name] = cluster.name

        for service in analysis.services:
            tool_name, params = self._get_aws_tool_for_service(service)

            tool_sequence.append(
                ToolCall(
                    tool_name=tool_name,
                    parameters={
                        "name": service.name,
                        "cluster_name": service_to_cluster_map.get(service.name),
                        **params,  # Correctly unpack the returned params
                    },
                    execution_order=order,
                )
            )
            order += 1

        logger.info("🔍 CREATING CONNECTIONS:")
        for conn in analysis.connections:
            # Enhanced connection styling
            connection_params = {
                "source": conn.source,
                "target": conn.target,
                "label": conn.label or "",
                "color": "#1976d2",
                "penwidth": "2.0",
                "arrowsize": "1.1",
            }

            tool_sequence.append(
                ToolCall(
                    tool_name="connect_nodes",
                    parameters=connection_params,
                    execution_order=order,
                )
            )
            order += 1

        execution_plan = ExecutionPlan(
            tool_sequence=tool_sequence,
            cluster_strategy="llm_defined",
            layout_preference="LR",
            estimated_duration=len(tool_sequence),
            complexity_score=analysis.confidence_score,
        )

        return execution_plan

    async def handle_task(self, task_data: dict) -> dict:
        """Main entry point for the architect using the robust two-stage approach."""
        description = task_data.get("description")
        session_id = task_data.get("session_id")
        logger.info("ArchitectAgent received prompt for two-stage processing")

        if session_id:
            await self._emit_verbose_update(
                session_id,
                "🧠 ANALYZING INFRASTRUCTURE",
                "Using two-stage LLM pipeline for robust analysis...",
            )

        # Use the new two-stage LLM analysis
        analysis = await self._analyze_infrastructure(description)

        if session_id:
            if not analysis.errors or "Analysis provided by" in analysis.errors[0]:
                components_found = len(analysis.services)
                clusters_found = len(analysis.clusters)
                await self._emit_verbose_update(
                    session_id,
                    "📊 ANALYSIS COMPLETE",
                    f"Identified {components_found} components in {clusters_found} cluster(s)",
                )
            else:
                await self._emit_verbose_update(
                    session_id,
                    "⚠️ ANALYSIS WARNING",
                    f"LLM analysis encountered issues. Using fallback. Error: {analysis.errors[0]}",
                )

        if session_id:
            await self._emit_verbose_update(
                session_id,
                "⚙️ GENERATING EXECUTION PLAN",
                "Creating detailed implementation plan...",
            )

        plan = self.generate_execution_plan(analysis, description)

        if session_id:
            total_tools = len(plan.tool_sequence)
            connections = len(
                [
                    tool
                    for tool in plan.tool_sequence
                    if tool.tool_name == "connect_nodes"
                ]
            )
            await self._emit_verbose_update(
                session_id,
                "✅ EXECUTION PLAN READY",
                f"Generated {total_tools} operations including {connections} connections",
            )

        logger.info(
            "ArchitectAgent generated final plan successfully using two-stage LLM analysis"
        )
        return plan.model_dump()

    async def _emit_verbose_update(self, session_id: str, title: str, details: str):
        """Emit detailed progress updates for verbose communication"""
        if not session_id:
            return

        from .streaming import ProgressEvent, global_agui_streamer

        event = ProgressEvent(
            event_type="agent_verbose",
            agent_id=self.agent_id,
            message=f"{title}: {details}",
            progress_percent=20,  # Architect progress level
            session_id=session_id,
            metadata={"title": title, "details": details, "verbose": True},
        )

        await global_agui_streamer.emit_progress_event(event)
