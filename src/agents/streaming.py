"""
AG-UI Information Streaming System for Multi-Agent Workflow Visualization
"""

import json
import logging
from datetime import datetime
from typing import Any

from fastapi import WebSocket
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProgressEvent(BaseModel):
    """Progress event for AG-UI streaming"""

    event_type: str
    agent_id: str
    message: str
    progress_percent: float = Field(ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: str | None = None


class AgentState(BaseModel):
    """Current state of an agent"""

    agent_id: str
    status: str  # idle, working, completed, error
    current_task: str | None = None
    progress: float = 0
    last_update: datetime = Field(default_factory=datetime.now)


class WorkflowState(BaseModel):
    """Complete workflow state for AG-UI dashboard"""

    session_id: str
    overall_progress: float
    current_step: str
    agents: list[AgentState]
    connections: list[dict[str, str]]
    a2a_messages: list[dict[str, Any]] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.now)
    estimated_completion: datetime | None = None


class AGUIStreamer:
    """Manages information streams for AG-UI frontend integration"""

    def __init__(self):
        self._subscribers: set[WebSocket] = set()
        self._event_history: dict[str, list[ProgressEvent]] = {}
        self._workflow_states: dict[str, WorkflowState] = {}
        self._agent_states: dict[str, AgentState] = {}

    async def subscribe(self, websocket: WebSocket, session_id: str | None = None):
        """Subscribe WebSocket client to progress events"""
        await websocket.accept()
        self._subscribers.add(websocket)

        # Send current state if session_id provided
        if session_id and session_id in self._workflow_states:
            current_state = self._workflow_states[session_id]
            await self._send_to_websocket(
                websocket, {"type": "workflow_state", "data": current_state.dict()}
            )

        return websocket

    async def unsubscribe(self, websocket: WebSocket):
        """Unsubscribe WebSocket client"""
        self._subscribers.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass

    async def emit_progress_event(self, event: ProgressEvent):
        """Emit progress event to all subscribers"""
        # Store in history
        session_id = event.session_id or "default"
        if session_id not in self._event_history:
            self._event_history[session_id] = []
        self._event_history[session_id].append(event)

        # Update agent state
        await self._update_agent_state(event)

        # Broadcast to all subscribers
        await self._broadcast_event(event)

    async def _update_agent_state(self, event: ProgressEvent):
        """Update agent state based on progress event"""
        agent_state = self._agent_states.get(event.agent_id)

        if not agent_state:
            agent_state = AgentState(agent_id=event.agent_id, status="idle")
            self._agent_states[event.agent_id] = agent_state

        # Update based on event type
        if event.event_type == "agent_start":
            agent_state.status = "working"
            agent_state.current_task = event.metadata.get("task", "Processing")
            agent_state.progress = 0
        elif event.event_type == "agent_progress":
            agent_state.progress = event.progress_percent
        elif event.event_type == "agent_complete":
            agent_state.status = "completed"
            agent_state.progress = 100
        elif event.event_type == "agent_error":
            agent_state.status = "error"
        elif event.event_type == "agent_delegation":
            agent_state.current_task = event.message

        agent_state.last_update = datetime.now()

    async def _broadcast_event(self, event: ProgressEvent):
        """Broadcast event to all WebSocket subscribers"""
        # Create a simple, readable message for the frontend
        simple_message = {
            "type": "progress_update",
            "agent": event.agent_id,
            "message": event.message,
            "progress": event.progress_percent,
            "timestamp": datetime.now().isoformat(),
            "session_id": event.session_id,
        }

        disconnected = set()
        for websocket in self._subscribers:
            try:
                # Send the simple, readable message format for better frontend display
                await self._send_to_websocket(websocket, simple_message)
                logger.debug(f"Sent progress event: {simple_message['message']}")
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                disconnected.add(websocket)

        # Remove disconnected clients
        for websocket in disconnected:
            self._subscribers.discard(websocket)

    async def _send_to_websocket(self, websocket: WebSocket, message: dict[str, Any]):
        """Send message to specific WebSocket with proper datetime handling"""
        try:

            def json_serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return str(obj)

            json_str = json.dumps(message, default=json_serializer)
            await websocket.send_text(json_str)
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
            raise e

    async def start_workflow(self, session_id: str, description: str) -> WorkflowState:
        """Start new workflow session"""
        workflow_state = WorkflowState(
            session_id=session_id,
            overall_progress=0,
            current_step="Initializing",
            agents=[
                AgentState(agent_id="coordinator", status="idle"),
                AgentState(agent_id="architect", status="idle"),
                AgentState(agent_id="builder", status="idle"),
            ],
            connections=[
                {"from": "coordinator", "to": "architect", "type": "delegation"},
                {"from": "coordinator", "to": "builder", "type": "delegation"},
            ],
        )

        self._workflow_states[session_id] = workflow_state

        # Emit workflow start event
        start_event = ProgressEvent(
            event_type="workflow_start",
            agent_id="coordinator",
            message=f"Starting diagram generation: {description}",
            progress_percent=0,
            session_id=session_id,
            metadata={"description": description},
        )

        await self.emit_progress_event(start_event)
        return workflow_state

    async def update_workflow_progress(
        self, session_id: str, current_step: str, overall_progress: float
    ):
        """Update overall workflow progress"""
        if session_id in self._workflow_states:
            workflow_state = self._workflow_states[session_id]
            workflow_state.current_step = current_step
            workflow_state.overall_progress = overall_progress

            # Broadcast workflow update
            await self._broadcast_workflow_state(session_id, workflow_state)

    async def _broadcast_workflow_state(
        self, session_id: str, workflow_state: WorkflowState
    ):
        """Broadcast workflow state update"""
        message = {"type": "workflow_state", "data": workflow_state.model_dump()}

        disconnected = set()
        for websocket in self._subscribers:
            try:
                await self._send_to_websocket(websocket, message)
            except Exception:
                disconnected.add(websocket)

        # Remove disconnected clients
        for websocket in disconnected:
            self._subscribers.discard(websocket)

    async def track_agent_delegation(
        self,
        session_id: str,
        delegating_agent: str,
        target_agent: str,
        task_description: str,
    ):
        """Track agent delegation for visualization"""
        event = ProgressEvent(
            event_type="agent_delegation",
            agent_id=delegating_agent,
            message=f"Delegating to {target_agent}: {task_description}",
            progress_percent=0,
            session_id=session_id,
            metadata={
                "target_agent": target_agent,
                "task": task_description,
                "delegation_type": "async",
            },
        )

        await self.emit_progress_event(event)

    async def track_a2a_message(
        self,
        session_id: str,
        sender: str,
        recipient: str,
        message_type: str,
        payload: dict[str, Any],
    ):
        """Track A2A protocol messages"""
        if session_id in self._workflow_states:
            workflow_state = self._workflow_states[session_id]

            message_data = {
                "timestamp": datetime.now().isoformat(),
                "sender": sender,
                "recipient": recipient,
                "message_type": message_type,
                "payload": payload,
            }

            workflow_state.a2a_messages.append(message_data)
            await self._broadcast_workflow_state(session_id, workflow_state)

    async def get_workflow_state(self, session_id: str) -> WorkflowState | None:
        """Get the current state of a workflow"""
        return self._workflow_states.get(session_id)

    async def get_event_history(self, session_id: str) -> list[ProgressEvent]:
        """Get the event history for a session"""
        return self._event_history.get(session_id, [])

    async def cleanup_session(self, session_id: str):
        """Clean up resources for a completed session"""
        if session_id in self._event_history:
            del self._event_history[session_id]
        if session_id in self._workflow_states:
            del self._workflow_states[session_id]

    def get_active_sessions(self) -> list[str]:
        """Get a list of all active session IDs"""
        return list(self._workflow_states.keys())

    def get_subscriber_count(self) -> int:
        """Get number of active subscribers"""
        return len(self._subscribers)


# Global AGUIStreamer instance
global_agui_streamer = AGUIStreamer()
