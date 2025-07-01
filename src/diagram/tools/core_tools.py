"""
Core Tools for Diagram Lifecycle Management

Contains tools for diagram initialization and rendering.
"""

from typing import Any

from src.diagram.engine import DiagramEngine

from .base_tool import BaseTool


class InitializeDiagramTool(BaseTool):
    """Tool for initializing a new diagram with optional graph attributes."""

    name = "initialize_diagram"
    description = "Initializes a new diagram with optional graph attributes"

    def validate_parameters(self, **kwargs) -> dict[str, Any]:
        """Validate initialization parameters."""
        # Set defaults for optional parameters
        validated = {
            "title": kwargs.get("title", "My Diagram"),
            "graph_attr": kwargs.get("graph_attr", {}),
        }

        # Validate title
        if not isinstance(validated["title"], str):
            raise ValueError("Title must be a string")

        # Validate graph_attr
        if not isinstance(validated["graph_attr"], dict):
            raise ValueError("graph_attr must be a dictionary")

        return validated

    def _validate_engine_state(self, engine: DiagramEngine) -> None:
        """For initialization, we don't require an existing diagram."""
        # This tool creates the diagram, so we don't validate existing diagram state
        pass

    async def execute(self, engine: DiagramEngine, **kwargs) -> None:
        """Execute diagram initialization."""
        title = kwargs["title"]
        graph_attr = kwargs["graph_attr"]

        self.logger.info(f"Initializing diagram: {title}")

        # Call the engine's initialization method
        engine.initialize_diagram(title=title, graph_attr=graph_attr)

        self.logger.debug(f"Diagram '{title}' initialized successfully")


class RenderDiagramTool(BaseTool):
    """Tool for rendering the final diagram to an image format."""

    name = "render_diagram"
    description = "Renders the final diagram to PNG, SVG, or PDF format"

    def validate_parameters(self, **kwargs) -> dict[str, Any]:
        """Validate rendering parameters."""
        output_format = kwargs.get("output_format", "png")
        dry_run = kwargs.get("dry_run", False)

        # Validate output format
        valid_formats = {"png", "svg", "pdf"}
        if output_format not in valid_formats:
            raise ValueError(
                f"Invalid output format '{output_format}'. Must be one of: {valid_formats}"
            )

        if not isinstance(dry_run, bool):
            raise ValueError("dry_run must be a boolean")

        return {"output_format": output_format, "dry_run": dry_run}

    async def execute(self, engine: DiagramEngine, **kwargs) -> dict[str, Any]:
        """Execute diagram rendering."""
        output_format = kwargs["output_format"]
        dry_run = kwargs.get("dry_run", False)

        self.logger.info(f"Rendering diagram to {output_format.upper()} format")

        # Call the engine's render method
        result = engine.render(output_format=output_format, dry_run=dry_run)

        # Add some additional metadata to the result
        if result.get("success", False):
            components_count = len(result.get("components_used", []))
            self.logger.info(
                f"Diagram rendered successfully with {components_count} components"
            )
        else:
            self.logger.error("Diagram rendering failed")

        return result
