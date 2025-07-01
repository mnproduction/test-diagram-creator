# src/validation/rules.py

from ..core.models import DiagramSpec, ValidationResult
from .framework import ValidationRule

# --- Syntax Layer Rules ---


async def check_for_required_parameters(spec: DiagramSpec) -> ValidationResult:
    """Checks if the diagram specification contains all required parameters."""
    issues = []
    if not hasattr(spec, "pattern_name"):
        issues.append("Missing required parameter: 'pattern_name'.")
    if not hasattr(spec, "parameters"):
        issues.append("Missing required parameter: 'parameters'.")
    if not hasattr(spec, "metadata"):
        issues.append("Missing required parameter: 'metadata'.")

    if issues:
        return ValidationResult(is_valid=False, issues=issues)
    return ValidationResult(is_valid=True)


async def check_parameter_types(spec: DiagramSpec) -> ValidationResult:
    """Checks if parameters have the correct data types."""
    # This is a placeholder. A real implementation would have a schema
    # to validate against for each pattern.
    if not isinstance(spec.parameters, dict):
        return ValidationResult(
            is_valid=False, issues=["'parameters' must be a dictionary."]
        )
    return ValidationResult(is_valid=True)


# --- Structure Layer Rules ---


async def check_for_orphaned_nodes(spec: DiagramSpec) -> ValidationResult:
    """Checks for any nodes that are defined but not connected to anything."""
    # Placeholder implementation
    # A real implementation would analyze the generated graph structure.
    return ValidationResult(is_valid=True)


async def check_for_circular_dependencies(spec: DiagramSpec) -> ValidationResult:
    """Checks for any circular dependencies between nodes."""
    # Placeholder implementation
    return ValidationResult(is_valid=True)


# --- Rule Registration ---


def get_all_rules() -> list[ValidationRule]:
    """Returns a list of all validation rules."""
    return [
        # Syntax Rules
        ValidationRule(
            "required_parameters", check_for_required_parameters, "syntax", priority=1
        ),
        ValidationRule("parameter_types", check_parameter_types, "syntax", priority=2),
        # Structure Rules
        ValidationRule(
            "orphaned_nodes", check_for_orphaned_nodes, "structure", priority=1
        ),
        ValidationRule(
            "circular_dependencies",
            check_for_circular_dependencies,
            "structure",
            priority=2,
        ),
    ]
