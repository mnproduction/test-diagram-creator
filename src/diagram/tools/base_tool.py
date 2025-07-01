"""
Base Tool Abstract Class for Modular Diagram Generation Framework
"""

import logging
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from src.diagram.engine import DiagramEngine


@dataclass
class ToolResult:
    """Result wrapper for tool execution with comprehensive error information."""

    success: bool
    result: Any = None
    error: str | None = None
    error_type: str | None = None
    context: dict[str, Any] | None = None
    execution_time_ms: float | None = None

    @classmethod
    def success_result(
        cls, result: Any, execution_time_ms: float = None
    ) -> "ToolResult":
        """Create a successful result."""
        return cls(success=True, result=result, execution_time_ms=execution_time_ms)

    @classmethod
    def error_result(
        cls,
        error: Exception,
        context: dict[str, Any] = None,
        execution_time_ms: float = None,
    ) -> "ToolResult":
        """Create an error result with context."""
        return cls(
            success=False,
            error=str(error),
            error_type=type(error).__name__,
            context=context or {},
            execution_time_ms=execution_time_ms,
        )


class BaseTool(ABC):
    """Abstract base class for all diagram generation tools."""

    name: str
    description: str

    def __init__(self):
        """Initialize the tool with optional features."""
        self._logger: logging.Logger | None = None
        self._execution_count: int = 0

    @property
    def logger(self) -> logging.Logger:
        """Lazy-loaded logger for the tool."""
        if self._logger is None:
            self._logger = logging.getLogger(f"tool.{self.name}")
        return self._logger

    @abstractmethod
    async def execute(self, engine: DiagramEngine, **kwargs) -> Any:
        """Execute the tool's operation with the provided engine and parameters."""
        pass

    def validate_parameters(self, **kwargs) -> dict[str, Any]:
        """Validate and process parameters for the tool."""
        return kwargs

    def _validate_engine_state(self, engine: DiagramEngine) -> None:
        """Validate the engine state before tool execution."""
        if not engine.diagram:
            raise ValueError(
                f"DiagramEngine not properly initialized for tool '{self.name}'"
            )

    @asynccontextmanager
    async def _execution_context(self, engine: DiagramEngine, **kwargs):
        """Context manager for tool execution with timing and logging."""
        start_time = time.time()
        self._execution_count += 1
        execution_id = f"{self.name}_{self._execution_count}"

        self.logger.debug(f"[{execution_id}] Starting execution with params: {kwargs}")

        try:
            self._validate_engine_state(engine)
            validated_params = self.validate_parameters(**kwargs)
            yield validated_params
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.logger.error(
                f"[{execution_id}] Tool execution failed after {execution_time:.1f}ms: {e}"
            )
            raise
        else:
            execution_time = (time.time() - start_time) * 1000
            self.logger.debug(
                f"[{execution_id}] Tool execution completed in {execution_time:.1f}ms"
            )

    async def execute_with_validation(self, engine: DiagramEngine, **kwargs) -> Any:
        """Execute tool with parameter validation and enhanced logging."""
        async with self._execution_context(engine, **kwargs) as validated_params:
            return await self.execute(engine, **validated_params)

    async def safe_execute(self, engine: DiagramEngine, **kwargs) -> ToolResult:
        """Execute tool with comprehensive error handling and result wrapping."""
        start_time = time.time()

        try:
            async with self._execution_context(engine, **kwargs) as validated_params:
                result = await self.execute(engine, **validated_params)
                execution_time = (time.time() - start_time) * 1000
                return ToolResult.success_result(result, execution_time)

        except KeyError as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                ValueError(f"Missing required parameter: {e}"),
                context={
                    "missing_parameter": str(e),
                    "available_parameters": list(kwargs.keys()),
                },
                execution_time_ms=execution_time,
            )

        except ValueError as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                e, context={"parameters": kwargs}, execution_time_ms=execution_time
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                RuntimeError(f"Unexpected error in {self.name}: {e}"),
                context={"parameters": kwargs, "original_error": str(e)},
                execution_time_ms=execution_time,
            )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
