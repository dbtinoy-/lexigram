"""Base filter compiler and registry for backend-specific translation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lexigram.contracts.data.vector.filters import (
    MetadataCondition,
    MetadataConditionGroup,
    MetadataFilter,
)
from lexigram.vector.exceptions import FilterCompilationError


class FilterCompiler(ABC):
    """Compile a MetadataFilter tree into a backend-native expression.

    Each backend subclasses this and implements the leaf/group visitors.
    """

    def __init__(self, backend_name: str) -> None:
        """Initialize with backend name for error messages."""
        self._backend = backend_name

    def compile(self, filter: MetadataFilter) -> Any:
        """Compile a filter tree to backend-native format.

        Raises:
            FilterCompilationError: If the filter cannot be compiled.
        """
        try:
            return self._visit(filter)
        except FilterCompilationError:
            raise
        except (
            Exception
        ) as exc:  # any non-FilterCompilationError re-raised as domain error
            raise FilterCompilationError(
                str(exc),
                self._backend,
            ) from exc

    def _visit(self, node: MetadataFilter) -> Any:
        """Dispatch to condition or group visitor."""
        if isinstance(node, MetadataCondition):
            return self._visit_condition(node)
        if isinstance(node, MetadataConditionGroup):
            return self._visit_group(node)
        raise FilterCompilationError(
            f"Unknown filter node type: {type(node).__name__}",
            self._backend,
        )

    @abstractmethod
    def _visit_condition(self, condition: MetadataCondition) -> Any:
        """Compile a single condition to backend format."""

    @abstractmethod
    def _visit_group(self, group: MetadataConditionGroup) -> Any:
        """Compile a condition group to backend format."""
