"""
Connection Tools for Diagram Generation

Contains tools for creating connections between diagram nodes.
"""

from typing import Any

from src.diagram.engine import DiagramEngine

from .base_tool import BaseTool


class ConnectNodesTool(BaseTool):
    """Tool for creating connections between diagram nodes."""

    name = "connect_nodes"
    description = "Creates connections between diagram nodes with optional styling"

    # Valid connection styling parameters (from DiagramEngine implementation)
    VALID_STYLE_PARAMS = {
        "color",
        "penwidth",
        "arrowsize",
        "style",
        "fontcolor",
        "fontsize",
    }

    def validate_parameters(self, **kwargs) -> dict[str, Any]:
        """Validate node connection parameters."""
        # Required parameters
        required_params = ["source", "target"]
        for param in required_params:
            if param not in kwargs:
                raise KeyError(f"Missing required parameter: {param}")

        # Extract and validate parameters
        source = kwargs["source"]
        target = kwargs["target"]
        label = kwargs.get("label", "")

        # Validate source node name
        if not isinstance(source, str) or not source.strip():
            raise ValueError("Source node name must be a non-empty string")

        # Validate target node name
        if not isinstance(target, str) or not target.strip():
            raise ValueError("Target node name must be a non-empty string")

        # Validate label if provided
        if label and not isinstance(label, str):
            raise ValueError("Label must be a string if provided")

        # Validate that source and target are different
        if source.strip() == target.strip():
            raise ValueError("Source and target nodes must be different")

        # Prepare validated parameters
        validated = {"source": source.strip(), "target": target.strip(), "label": label}

        # Extract and validate styling parameters
        styling_kwargs = {}
        for key, value in kwargs.items():
            if key not in ["source", "target", "label"]:
                if key in self.VALID_STYLE_PARAMS:
                    styling_kwargs[key] = value
                else:
                    self.logger.warning(
                        f"Unknown styling parameter '{key}' - will be passed through"
                    )
                    styling_kwargs[key] = value

        # Add styling parameters to validated dict
        validated.update(styling_kwargs)

        return validated

    async def execute(self, engine: DiagramEngine, **kwargs) -> None:
        """Execute node connection."""
        source = kwargs["source"]
        target = kwargs["target"]
        label = kwargs.get("label", "")

        # Extract styling parameters
        styling_kwargs = {
            k: v for k, v in kwargs.items() if k not in ["source", "target", "label"]
        }

        self.logger.info(
            f"Connecting '{source}' -> '{target}'"
            f"{f' (label: {label})' if label else ''}"
        )

        # Log styling parameters if provided
        if styling_kwargs:
            self.logger.debug(f"Connection styling: {styling_kwargs}")

        # Call the engine's connection method
        engine.connect_nodes(
            source=source, target=target, label=label, **styling_kwargs
        )

        self.logger.debug(f"Connection '{source}' -> '{target}' created successfully")
