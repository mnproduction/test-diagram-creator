# src/validation/framework.py

import asyncio
import logging
from collections.abc import Callable

from ..core.exceptions import ValidationException
from ..core.models import DiagramSpec, ValidationResult

logger = logging.getLogger(__name__)


class ValidationRule:
    """A single, executable validation rule."""

    def __init__(self, name: str, function: Callable, layer: str, priority: int = 100):
        self.name = name
        self.function = function
        self.layer = layer
        self.priority = priority


class RuleRegistry:
    """Manages the registration and retrieval of validation rules."""

    def __init__(self):
        self._rules: dict[str, list[ValidationRule]] = {
            "syntax": [],
            "structure": [],
            "visual": [],
            "compliance": [],
        }

    def register(self, rule: ValidationRule):
        """Registers a new validation rule."""
        if rule.layer not in self._rules:
            raise ValidationException(f"Invalid validation layer: {rule.layer}")
        self._rules[rule.layer].append(rule)
        self._rules[rule.layer].sort(key=lambda r: r.priority)
        logger.debug(
            f"Registered rule '{rule.name}' in layer '{rule.layer}' with priority {rule.priority}"
        )

    def get_rules_for_layer(self, layer: str) -> list[ValidationRule]:
        """Retrieves all rules for a specific layer, sorted by priority."""
        return self._rules.get(layer, [])


class RuleEngine:
    """Executes validation rules for a given diagram specification."""

    def __init__(self, registry: RuleRegistry):
        self.registry = registry

    async def execute_layer(
        self, layer: str, spec: DiagramSpec
    ) -> list[ValidationResult]:
        """Executes all rules for a specific layer in parallel."""
        rules = self.registry.get_rules_for_layer(layer)
        if not rules:
            return []

        tasks = [rule.function(spec) for rule in rules]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Rule '{rules[i].name}' failed with exception: {result}",
                    exc_info=result,
                )
                processed_results.append(
                    ValidationResult(
                        is_valid=False,
                        issues=[f"Rule '{rules[i].name}' threw an exception."],
                    )
                )
            elif isinstance(result, ValidationResult):
                processed_results.append(result)

        return processed_results


class ValidationFramework:
    """
    Orchestrates the entire multi-layer validation process.
    """

    def __init__(self, rule_registry: RuleRegistry):
        self.engine = RuleEngine(rule_registry)
        self.layers = ["syntax", "structure", "visual", "compliance"]

    async def validate(self, spec: DiagramSpec) -> ValidationResult:
        """
        Executes the full, multi-layer validation pipeline.
        Stops at the first layer with validation failures.
        """
        all_issues = []

        for layer in self.layers:
            logger.info(f"Executing validation layer: {layer.upper()}")
            layer_results = await self.engine.execute_layer(layer, spec)

            layer_issues = [
                issue
                for res in layer_results
                if not res.is_valid
                for issue in res.issues
            ]

            if layer_issues:
                all_issues.extend(layer_issues)
                logger.warning(
                    f"Validation failed at layer '{layer}' with issues: {layer_issues}"
                )
                # Stop at the first layer that has issues
                return ValidationResult(is_valid=False, issues=all_issues)

        logger.info("All validation layers passed successfully.")
        return ValidationResult(is_valid=True, issues=[])
