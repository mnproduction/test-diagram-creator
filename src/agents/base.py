"""
Base classes and types for PydanticAI multi-agent architecture
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class MessageType(Enum):
    """A2A Protocol message types"""

    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    PROGRESS_UPDATE = "progress_update"
    ERROR_NOTIFICATION = "error_notification"
    AGENT_REGISTRATION = "agent_registration"
    HEALTH_CHECK = "health_check"


class A2AMessage(BaseModel):
    """Agent-to-agent communication message"""

    message_type: MessageType
    sender_agent: str
    recipient_agent: str
    payload: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class DiagramContext:
    """Shared context for all diagram generation agents"""

    original_description: str
    user_requirements: list[str] = None
    output_format: str = "png"
    show_labels: bool = True
    stream_progress: bool = False
    session_id: str = None

    def __post_init__(self):
        if self.user_requirements is None:
            self.user_requirements = []
        if self.session_id is None:
            self.session_id = str(uuid.uuid4())


class ComponentType(str, Enum):
    """Supported diagram component types"""

    AWS_COMPUTE = "aws_compute"
    AWS_DATABASE = "aws_database"
    AWS_NETWORK = "aws_network"
    AWS_STORAGE = "aws_storage"
    GENERIC = "generic"
    CLUSTER = "cluster"
    CONNECTION = "connection"


class ServiceComponent(BaseModel):
    """Individual service component in diagram"""

    name: str
    component_type: ComponentType
    service_name: str  # e.g., "ec2", "rds", "alb"
    description: str | None = None
    cluster: str | None = None


class ClusterDefinition(BaseModel):
    """Cluster grouping definition"""

    name: str
    label: str
    services: list[str]
    parent: str | None = None  # New field for nesting
    description: str | None = None


class ConnectionSpec(BaseModel):
    """Connection between services"""

    source: str
    target: str
    connection_type: str = "standard"
    label: str | None = None
    bidirectional: bool = False


class ComponentAnalysis(BaseModel):
    """Result of analyzer agent"""

    services: list[ServiceComponent]
    clusters: list[ClusterDefinition]
    connections: list[ConnectionSpec]
    confidence_score: float = Field(ge=0, le=1)
    errors: list[str] = Field(default_factory=list)


class ToolCall(BaseModel):
    """Individual tool execution specification"""

    tool_name: str
    parameters: dict[str, Any]
    execution_order: int
    depends_on: list[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    """Architect agent execution plan"""

    tool_sequence: list[ToolCall]
    cluster_strategy: str
    layout_preference: str
    estimated_duration: int  # seconds
    complexity_score: float = Field(ge=0, le=1)


class DiagramResult(BaseModel):
    """Final diagram generation result"""

    success: bool
    image_data: str | None = None  # base64 encoded
    components_used: list[str]
    generation_time_ms: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DiagramResponse(BaseModel):
    """Complete response from coordinator agent"""

    success: bool
    result: DiagramResult | None = None
    analysis: ComponentAnalysis | None = None
    execution_plan: ExecutionPlan | None = None
    agent_workflow: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


@dataclass
class AgentMetadata:
    """Metadata for agent registration"""

    agent_id: str
    capabilities: list[str]
    output_types: list[str]
    deps_type: str
    status: str = "active"
    last_seen: datetime = None

    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.now()


class A2AProtocol(Protocol):
    """Protocol for agent-to-agent communication"""

    async def send_message(self, message: A2AMessage) -> None:
        """Send message to another agent"""
        ...

    async def receive_message(self) -> A2AMessage:
        """Receive message from another agent"""
        ...

    async def subscribe_to_agent(self, agent_id: str) -> None:
        """Subscribe to messages from specific agent"""
        ...


class MessageBus:
    """Central message bus for A2A protocol"""

    def __init__(self):
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._message_history: list[A2AMessage] = []

    async def subscribe(self, agent_id: str, queue: asyncio.Queue) -> None:
        """Subscribe agent to message bus"""
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = set()
        self._subscribers[agent_id].add(queue)

    async def unsubscribe(self, agent_id: str, queue: asyncio.Queue) -> None:
        """Unsubscribe agent from message bus"""
        if agent_id in self._subscribers:
            self._subscribers[agent_id].discard(queue)

    async def send_message(self, message: A2AMessage) -> None:
        """Send message to recipient agent"""
        self._message_history.append(message)

        recipient_queues = self._subscribers.get(message.recipient_agent, set())
        for queue in recipient_queues:
            try:
                await queue.put(message)
            except Exception as e:
                print(f"Error delivering message to {message.recipient_agent}: {e}")

    async def broadcast_message(self, message: A2AMessage) -> None:
        """Broadcast message to all subscribed agents"""
        self._message_history.append(message)

        for agent_id, queues in self._subscribers.items():
            if agent_id != message.sender_agent:  # Don't send to sender
                for queue in queues:
                    try:
                        await queue.put(message)
                    except Exception as e:
                        print(f"Error broadcasting to {agent_id}: {e}")


class AgentRegistry:
    """Central registry for A2A protocol agent discovery"""

    def __init__(self):
        self._agents: dict[str, AgentMetadata] = {}
        self._message_bus = MessageBus()

    async def register_agent(self, metadata: AgentMetadata) -> None:
        """Register agent in the registry"""
        self._agents[metadata.agent_id] = metadata

        # Send registration message
        registration_msg = A2AMessage(
            message_type=MessageType.AGENT_REGISTRATION,
            sender_agent=metadata.agent_id,
            recipient_agent="registry",
            payload={"capabilities": metadata.capabilities},
        )
        await self._message_bus.broadcast_message(registration_msg)

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister agent from registry"""
        if agent_id in self._agents:
            del self._agents[agent_id]

    async def find_agent_by_capability(self, capability: str) -> AgentMetadata | None:
        """Find agent that provides specific capability"""
        for metadata in self._agents.values():
            if capability in metadata.capabilities:
                return metadata
        return None

    async def get_all_agents(self) -> dict[str, AgentMetadata]:
        """Get all registered agents"""
        return self._agents.copy()

    async def delegate_task(
        self, sender_agent: str, task_spec: dict[str, Any], target_agent: str
    ) -> str:
        """Delegate task to target agent"""
        correlation_id = str(uuid.uuid4())

        message = A2AMessage(
            message_type=MessageType.TASK_REQUEST,
            sender_agent=sender_agent,
            recipient_agent=target_agent,
            payload={"task": task_spec},
            correlation_id=correlation_id,
        )

        await self._message_bus.send_message(message)
        return correlation_id

    def get_message_bus(self) -> MessageBus:
        """Get reference to message bus"""
        return self._message_bus


# Global registry instance
global_agent_registry = AgentRegistry()
