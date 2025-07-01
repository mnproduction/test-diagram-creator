"""
Coordinator Agent for orchestrating multi-agent diagram generation workflow
"""

from typing import Any

import structlog
from pydantic_ai import Agent

from src.core.settings import gemini_settings

from .agent_settings import COORDINATOR_SYSTEM_PROMPT
from .architect import ArchitectAgent
from .base import DiagramContext, DiagramResponse, DiagramResult, ExecutionPlan
from .builder import BuilderAgent
from .streaming import ProgressEvent, global_agui_streamer

logger = structlog.get_logger(__name__)


class CoordinatorAgent:
    """
    Coordinator Agent that orchestrates the entire diagram generation workflow
    by delegating tasks to specialized agents.
    """

    def __init__(
        self, architect: ArchitectAgent, builder: BuilderAgent, model: str | None = None
    ):
        self.agent_id = "coordinator"
        self.model = model or gemini_settings.model_name
        self.architect = architect
        self.builder = builder

        self.agent = Agent(model=self.model, system_prompt=COORDINATOR_SYSTEM_PROMPT)

    async def generate_diagram(self, context: DiagramContext) -> DiagramResponse:
        """
        Main entry point for diagram generation workflow
        """
        session_id = context.session_id
        logger.info(
            "Starting diagram generation",
            session_id=session_id,
            description=context.original_description,
        )

        # Initialize workflow in AG-UI
        await self._start_workflow(session_id, context.original_description)

        try:
            # --- Stage 1 & 2 COMBINED: Architecture ---
            await self._send_progress_update(
                session_id,
                "Planning Architecture",
                "Handing off to Architect Agent for full planning...",
                20,
            )
            await self._emit_agent_delegation(
                session_id,
                "coordinator",
                "architect",
                "Parse prompt and generate execution plan",
            )

            # The architect now takes the raw description directly with session_id for verbose updates
            plan_dict = await self.architect.handle_task(
                {"description": context.original_description, "session_id": session_id}
            )
            plan_result = ExecutionPlan(**plan_dict)
            await self._send_progress_update(
                session_id,
                "Architecture Planned",
                "Received complete execution plan.",
                60,
            )

            # --- Stage 3: Building ---
            await self._send_progress_update(
                session_id, "Building Diagram", "Handing off to Builder Agent...", 70
            )
            await self._emit_agent_delegation(
                session_id, "coordinator", "builder", "Execute plan and render diagram"
            )

            diagram_dict = await self.builder.handle_task(
                {"execution_plan": plan_result.model_dump(), "session_id": session_id}
            )
            diagram_result = DiagramResult(**diagram_dict)
            await self._send_progress_update(
                session_id, "Diagram Complete", "Final image generated.", 90
            )

            logger.info(
                "Coordinator agent finished successfully", session_id=session_id
            )
            return DiagramResponse(
                success=True,
                result=diagram_result,
                execution_plan=plan_result,
            )

        except Exception as e:
            logger.error(
                "Error during diagram generation",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            await self._send_progress_update(session_id, "Error", str(e), 100)
            return DiagramResponse(
                success=False, errors=[f"Coordinator error: {str(e)}"]
            )
        finally:
            logger.info("Coordinator agent finished", session_id=session_id)

    async def _send_progress_update(
        self, session_id: str, status: str, details: any, progress: int
    ):
        """Send progress update to AG-UI streaming system"""
        logger.debug(
            "Sending progress update",
            session_id=session_id,
            progress=progress,
            status=status,
            details=details,
        )

        # Create and emit progress event
        event = ProgressEvent(
            event_type="agent_progress",
            agent_id=self.agent_id,
            message=f"{status}: {details}",
            progress_percent=float(progress),
            session_id=session_id,
            metadata={"status": status, "details": str(details)},
        )

        await global_agui_streamer.emit_progress_event(event)
        await global_agui_streamer.update_workflow_progress(
            session_id, status, float(progress)
        )

    async def _start_workflow(self, session_id: str, description: str):
        """Initialize the workflow in AG-UI with our simplified architecture"""
        # Override the default workflow to match our simplified architecture
        await global_agui_streamer.start_workflow(session_id, description)

    async def _emit_agent_delegation(
        self, session_id: str, from_agent: str, to_agent: str, task: str
    ):
        """Emit agent delegation event for AG-UI visualization"""
        await global_agui_streamer.track_agent_delegation(
            session_id, from_agent, to_agent, task
        )

        # Also emit individual agent start events
        start_event = ProgressEvent(
            event_type="agent_start",
            agent_id=to_agent,
            message=f"Starting task: {task}",
            progress_percent=0,
            session_id=session_id,
            metadata={"task": task, "delegated_by": from_agent},
        )
        await global_agui_streamer.emit_progress_event(start_event)

    async def get_status(self) -> dict[str, Any]:
        """Returns the current status of the coordinator and its agents."""
        return {
            "agent_id": self.agent_id,
            "status": "active",
            "pending_tasks": 0,
            "agents": {
                "architect": "active",
                "builder": "active",
            },
        }
