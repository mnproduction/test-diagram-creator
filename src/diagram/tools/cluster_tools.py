"""
Cluster Tools for Diagram Generation

Contains tools for creating and managing diagram clusters.
"""

from typing import Any

from src.diagram.engine import DiagramEngine

from .base_tool import BaseTool


class CreateClusterTool(BaseTool):
    """Tool for creating clusters to group related diagram components."""

    name = "create_cluster"
    description = "Creates a cluster to group related diagram components"

    def validate_parameters(self, **kwargs) -> dict[str, Any]:
        """Validate cluster creation parameters."""
        # Required parameters
        required_params = ["name", "label"]
        for param in required_params:
            if param not in kwargs:
                raise KeyError(f"Missing required parameter: {param}")

        # Extract and validate parameters
        name = kwargs["name"]
        label = kwargs["label"]
        graph_attr = kwargs.get("graph_attr", {})
        parent_name = kwargs.get("parent_name")  # Parent cluster

        # Validate name
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Cluster name must be a non-empty string")

        # Validate label
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Cluster label must be a non-empty string")

        # Validate graph_attr
        if not isinstance(graph_attr, dict):
            raise ValueError("graph_attr must be a dictionary")

        # Validate parent cluster_name if provided
        if parent_name is not None:
            if not isinstance(parent_name, str) or not parent_name.strip():
                raise ValueError(
                    "Parent cluster name must be a non-empty string if provided"
                )

        return {
            "name": name.strip(),
            "label": label.strip(),
            "graph_attr": graph_attr,
            "parent_name": parent_name.strip() if parent_name else None,
        }

    async def execute(self, engine: DiagramEngine, **kwargs) -> None:
        """Execute cluster creation."""
        name = kwargs["name"]
        label = kwargs["label"]
        graph_attr = kwargs["graph_attr"]
        parent_name = kwargs.get("parent_name")

        self.logger.info(
            f"Creating cluster '{name}' (label: '{label}')"
            f"{f' inside parent cluster {parent_name}' if parent_name else ''}"
        )

        # Log graph attributes if provided
        if graph_attr:
            self.logger.debug(f"Cluster '{name}' graph attributes: {graph_attr}")

        # Call the engine's cluster creation method
        engine.create_cluster(
            name=name, label=label, graph_attr=graph_attr, cluster_name=parent_name
        )

        self.logger.debug(f"Cluster '{name}' created successfully")
