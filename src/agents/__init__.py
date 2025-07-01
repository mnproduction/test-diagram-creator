"""
Agent domain module for AI Diagram Creator

This module contains all the agents and related components for the multi-agent
diagram generation system.
"""

# Import all agent classes
from .architect import ArchitectAgent

# Import base classes and types
from .base import (
    A2AMessage,
    AgentMetadata,
    AgentRegistry,
    ClusterDefinition,
    ComponentAnalysis,
    ComponentType,
    ConnectionSpec,
    DiagramContext,
    DiagramResponse,
    DiagramResult,
    ExecutionPlan,
    MessageBus,
    MessageType,
    ServiceComponent,
)
from .builder import BuilderAgent
from .coordinator import CoordinatorAgent

# Create global registry instance
global_agent_registry = AgentRegistry()

# Export all public classes and instances
__all__ = [
    # Agent classes
    "CoordinatorAgent",
    "ArchitectAgent",
    "BuilderAgent",
    # Core data models
    "DiagramContext",
    "DiagramResponse",
    "ComponentAnalysis",
    "ExecutionPlan",
    "DiagramResult",
    # Component models
    "ServiceComponent",
    "ClusterDefinition",
    "ConnectionSpec",
    "ComponentType",
    # Communication models
    "MessageType",
    "A2AMessage",
    "AgentMetadata",
    "MessageBus",
    "AgentRegistry",
    # Global instances
    "global_agent_registry",
]
