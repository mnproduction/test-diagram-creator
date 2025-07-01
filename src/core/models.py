# src/core/models.py
from typing import Any

from pydantic import BaseModel


class DiagramSpec(BaseModel):
    """
    Represents the high-level specification for a diagram to be generated.
    This model will be expanded as we build out the template and diagram domains.
    """

    pattern_name: str
    parameters: dict[str, Any]
    metadata: dict[str, Any] = {}


class ValidationResult(BaseModel):
    """
    Represents the outcome of a validation check.
    """

    is_valid: bool
    issues: list[str] = []
