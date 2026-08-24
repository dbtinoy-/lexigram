"""Filter specification types for admin data queries.

Composable via ``&`` into :class:`CombinedSpec` trees consumed by data
sources that support structured where-clauses.
"""

from __future__ import annotations

# ============================================================================
# Filter SpecificationProtocol Types
# ============================================================================


class EqualSpec:
    """Filter specification for exact equality: column == value."""

    def __init__(self, field: str, value: object) -> None:
        """Initialize EqualSpec with field name and value to match."""
        self.field = field
        self.value = value

    def __and__(self, other: FilterSpec) -> CombinedSpec:
        """Combine with another spec using AND."""
        return CombinedSpec(specs=[self, other])


class InSpec:
    """Filter specification for IN query: column IN values."""

    def __init__(self, field: str, values: list[object]) -> None:
        """Initialize InSpec with field name and list of values."""
        self.field = field
        self.values = values

    def __and__(self, other: FilterSpec) -> CombinedSpec:
        """Combine with another spec using AND."""
        return CombinedSpec(specs=[self, other])


class GreaterThanOrEqualSpec:
    """Filter specification for >= comparison: column >= value."""

    def __init__(self, field: str, value: object) -> None:
        """Initialize GreaterThanOrEqualSpec with field name and value."""
        self.field = field
        self.value = value

    def __and__(self, other: FilterSpec) -> CombinedSpec:
        """Combine with another spec using AND."""
        return CombinedSpec(specs=[self, other])


class LessThanOrEqualSpec:
    """Filter specification for <= comparison: column <= value."""

    def __init__(self, field: str, value: object) -> None:
        """Initialize LessThanOrEqualSpec with field name and value."""
        self.field = field
        self.value = value

    def __and__(self, other: FilterSpec) -> CombinedSpec:
        """Combine with another spec using AND."""
        return CombinedSpec(specs=[self, other])


FilterSpec = EqualSpec | InSpec | GreaterThanOrEqualSpec | LessThanOrEqualSpec


class CombinedSpec:
    """Combined filter specification (AND of multiple specs)."""

    def __init__(self, specs: list[FilterSpec]) -> None:
        """Initialize CombinedSpec with list of filter specs."""
        self.specs = specs

    def __and__(self, other: FilterSpec) -> CombinedSpec:
        """Combine with another spec using AND."""
        return CombinedSpec(specs=[*self.specs, other])
