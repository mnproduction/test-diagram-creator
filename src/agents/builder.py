"""
Builder Agent for constructing the diagram from an execution plan.
"""

import asyncio

import structlog

from src.core.settings import gemini_settings
from src.diagram.engine import DiagramEngine
from src.diagram.tool_registry import ToolRegistry

from .base import (
    DiagramResult,
    ExecutionPlan,
)

logger = structlog.get_logger(__name__)


class BuilderAgent:
    """
    Builder Agent that executes a plan to construct the final diagram image
    using the diagrams package via a tool abstraction layer.
    """

    def __init__(self, diagram_engine: DiagramEngine = None, model: str | None = None):
        self.agent_id = "builder"
        self.model = model or gemini_settings.model_name
        if diagram_engine is None:
            diagram_engine = DiagramEngine()
        self.tool_registry = ToolRegistry(diagram_engine)
        self.message_queue = asyncio.Queue()

    async def handle_task(self, task_data: dict) -> dict:
        """Handles a task request from the Coordinator."""
        start_time = asyncio.get_event_loop().time()
        plan_data = task_data.get("execution_plan")
        session_id = task_data.get("session_id")

        logger.info("BuilderAgent received execution plan.", session_id=session_id)
        if not plan_data:
            logger.error(
                "No execution plan provided to BuilderAgent.", session_id=session_id
            )
            return DiagramResult(
                success=False, errors=["No execution plan provided"]
            ).model_dump()

        plan = ExecutionPlan(**plan_data)

        if session_id:
            await self._emit_verbose_update(
                session_id,
                "📋 EXECUTION PLAN LOADED",
                f"Ready to execute {len(plan.tool_sequence)} tools in sequence",
            )

        logger.info("Executing tool calls", num_tools=len(plan.tool_sequence))
        executed_tools = 0

        sorted_tool_sequence = sorted(
            plan.tool_sequence, key=lambda tc: tc.execution_order
        )
        logger.debug(
            "Tool execution sequence",
            sequence=[(t.tool_name, t.parameters) for t in sorted_tool_sequence],
        )

        for tool_call in sorted_tool_sequence:
            logger.debug(
                "Attempting to execute tool",
                tool_name=tool_call.tool_name,
                parameters=tool_call.parameters,
            )

            try:
                tool = self.tool_registry.get_tool(tool_call.tool_name)
                logger.debug("Tool found in registry", tool_name=tool_call.tool_name)
            except KeyError:
                logger.warning(
                    "Tool not found in registry",
                    tool_name=tool_call.tool_name,
                    available_tools=list(self.tool_registry.list_tools().keys()),
                )
                if session_id:
                    await self._emit_verbose_update(
                        session_id,
                        "⚠️ TOOL SKIPPED",
                        f"Tool '{tool_call.tool_name}' not found in registry",
                    )
                continue

            # Verbose communication for each tool
            if session_id:
                tool_description = self._get_tool_description(
                    tool_call.tool_name, tool_call.parameters
                )
                await self._emit_verbose_update(
                    session_id,
                    f"⚒️ EXECUTING TOOL {executed_tools + 1}/{len(plan.tool_sequence)}",
                    tool_description,
                )

            try:
                logger.debug(
                    "Executing tool",
                    tool_name=tool_call.tool_name,
                    params=tool_call.parameters,
                )

                # Execute the tool with the new pattern: tool.execute(engine, **params)
                _ = await tool.execute(
                    self.tool_registry.engine, **tool_call.parameters
                )

                executed_tools += 1
                logger.info(
                    "Tool executed successfully",
                    tool_name=tool_call.tool_name,
                    executed_count=executed_tools,
                    total_tools=len(plan.tool_sequence),
                )

                # Report successful execution
                if session_id:
                    await self._emit_verbose_update(
                        session_id,
                        "✅ TOOL COMPLETED",
                        f"{tool_call.tool_name} executed successfully",
                    )

            except Exception as e:
                logger.error(
                    "Tool execution failed",
                    tool_name=tool_call.tool_name,
                    error=str(e),
                    exc_info=True,
                )
                if session_id:
                    await self._emit_verbose_update(
                        session_id,
                        "❌ TOOL FAILED",
                        f"{tool_call.tool_name} failed: {str(e)}",
                    )
                end_time = asyncio.get_event_loop().time()
                return DiagramResult(
                    success=False,
                    errors=[f"Failed to execute tool {tool_call.tool_name}: {e}"],
                    components_used=[],
                    generation_time_ms=int((end_time - start_time) * 1000),
                ).model_dump()

        logger.info(
            "Tool execution complete",
            executed_tools=executed_tools,
            total_tools=len(plan.tool_sequence),
        )

        if session_id:
            await self._emit_verbose_update(
                session_id,
                "🎨 RENDERING DIAGRAM",
                "Converting execution plan to final PNG image...",
            )

        logger.info("Rendering final diagram...")
        try:
            render_tool = self.tool_registry.get_tool("render_diagram")
            if not render_tool:
                raise Exception("Render tool not found")

            # Default to dry_run=False for safety if not specified
            render_params = {
                "output_format": "png",
                "dry_run": task_data.get("dry_run", False),
            }

            # Execute the rendering tool with the new pattern
            final_result = await render_tool.execute(
                self.tool_registry.engine, **render_params
            )

            end_time = asyncio.get_event_loop().time()

            final_result["generation_time_ms"] = int((end_time - start_time) * 1000)
            logger.info(
                "Diagram rendered successfully",
                generation_time_ms=final_result["generation_time_ms"],
            )

            if session_id:
                components_count = len(final_result.get("components_used", []))
                await self._emit_verbose_update(
                    session_id,
                    "🏁 RENDERING COMPLETE",
                    f"Generated diagram with {components_count} components in {final_result['generation_time_ms']}ms",
                )

            return DiagramResult(**final_result).model_dump()

        except Exception as e:
            logger.error(
                "Failed to render the final diagram", error=str(e), exc_info=True
            )
            if session_id:
                await self._emit_verbose_update(
                    session_id,
                    "❌ RENDERING FAILED",
                    f"Failed to generate final image: {str(e)}",
                )
            end_time = asyncio.get_event_loop().time()
            return DiagramResult(
                success=False,
                errors=[f"Failed to render diagram: {e}"],
                components_used=[],
                generation_time_ms=int((end_time - start_time) * 1000),
            ).model_dump()

    def _get_tool_description(self, tool_name: str, parameters: dict) -> str:
        """Generate human-readable description of what each tool does"""
        if tool_name == "initialize_diagram":
            title = parameters.get("title", "Diagram")
            return f"Initializing '{title}' with layout settings"
        elif tool_name == "create_cluster":
            name = parameters.get("name", "cluster")
            label = parameters.get("label", "")
            return f"Creating cluster '{name}' with label '{label}'"
        elif tool_name == "create_aws_node":
            service = parameters.get("aws_service", "service")
            name = parameters.get("name", "node")
            label = parameters.get("label", name)
            cluster = parameters.get("cluster_name")
            location = f" in cluster '{cluster}'" if cluster else ""
            return f"Creating {service.upper()} node '{label}'{location}"
        elif tool_name == "connect_nodes":
            source = parameters.get("source", "source")
            target = parameters.get("target", "target")
            return f"Connecting '{source}' → '{target}'"
        elif tool_name == "render_diagram":
            format = parameters.get("output_format", "png")
            return f"Rendering final {format.upper()} image"
        else:
            return f"Executing {tool_name} with {len(parameters)} parameters"

    async def _emit_verbose_update(self, session_id: str, title: str, details: str):
        """Emit detailed progress updates for verbose communication"""
        from .streaming import ProgressEvent, global_agui_streamer

        event = ProgressEvent(
            event_type="agent_verbose",
            agent_id=self.agent_id,
            message=f"{title}: {details}",
            progress_percent=75,  # Mid-to-high progress for builder tasks
            session_id=session_id,
            metadata={"title": title, "details": details, "verbose": True},
        )

        await global_agui_streamer.emit_progress_event(event)
