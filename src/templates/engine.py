# src/templates/engine.py

import logging
from typing import Any

from pydantic import BaseModel

from ..core.exceptions import TemplateException
from ..core.models import DiagramSpec
from ..diagram.engine import DiagramEngine

logger = logging.getLogger(__name__)


class PatternTemplate(BaseModel):
    """Represents a template for an architectural pattern."""

    name: str
    description: str
    parameters: dict[str, Any]
    steps: list[dict[str, Any]]


class PatternLibrary:
    """Manages a collection of architectural pattern templates."""

    def __init__(self):
        self._patterns: dict[str, PatternTemplate] = {}
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Loads the default set of architectural patterns."""
        # In a real application, these would be loaded from YAML or JSON files.
        layered_arch = PatternTemplate(
            name="layered_architecture",
            description="A standard 3-tier layered architecture.",
            parameters={"layers": ["presentation", "business", "data"]},
            steps=[
                {
                    "action": "create_cluster",
                    "params": {"name": "presentation", "label": "Presentation Layer"},
                },
                {
                    "action": "create_cluster",
                    "params": {"name": "business", "label": "Business Logic Layer"},
                },
                {
                    "action": "create_cluster",
                    "params": {"name": "data", "label": "Data Access Layer"},
                },
            ],
        )
        self.register_pattern(layered_arch)

    def register_pattern(self, pattern: PatternTemplate):
        """Registers a new pattern."""
        self._patterns[pattern.name] = pattern
        logger.debug(f"Registered pattern: {pattern.name}")

    def get_pattern(self, name: str) -> PatternTemplate:
        """Retrieves a pattern by name."""
        pattern = self._patterns.get(name)
        if not pattern:
            raise TemplateException(f"Pattern '{name}' not found.")
        return pattern


class TemplateEngine:
    """
    Processes a DiagramSpec, resolves the pattern template, and uses the
    DiagramEngine to construct the diagram.
    """

    def __init__(self, diagram_engine: DiagramEngine, pattern_library: PatternLibrary):
        self.diagram_engine = diagram_engine
        self.pattern_library = pattern_library

    async def apply_template(self, spec: DiagramSpec):
        """Applies a pattern template to the diagram engine."""
        logger.info(f"Applying template for pattern: {spec.pattern_name}")
        pattern = self.pattern_library.get_pattern(spec.pattern_name)

        # This is a simplified implementation. A real implementation would
        # have a more sophisticated parameter binding and step execution logic.
        self.diagram_engine.initialize_diagram(title=pattern.description)

        for step in pattern.steps:
            action = step.get("action")
            params = step.get("params", {})

            tool_func = getattr(self.diagram_engine, action, None)
            if tool_func and callable(tool_func):
                try:
                    # Here we would merge spec.parameters with template params
                    tool_func(**params)
                except Exception as e:
                    raise TemplateException(
                        f"Failed to execute action '{action}': {e}"
                    ) from e
            else:
                raise TemplateException(
                    f"Action '{action}' not found in DiagramEngine."
                )

        logger.info(f"Template '{spec.pattern_name}' applied successfully.")
        # The final rendering will be called by the BuilderAgent.
