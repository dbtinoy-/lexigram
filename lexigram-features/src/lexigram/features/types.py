"""Type definitions for the feature-flag subsystem.

All dataclasses, enums, type aliases, and TypeVars used throughout the
feature-flag system live here.  No business logic; data definitions only.

Types:
    FlagType: Evaluation strategy enum for a feature flag.
    FlagValue: Type alias for boolean or variant-name evaluation result.
    Flag: Full flag definition including evaluation rules.
    FlagContext: Evaluation context (user, session, attributes).
    FlagEvaluation: Result of evaluating a flag for a given context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
from typing import Any

from lexigram.serialization import dumps_str


class FlagType(StrEnum):
    """Evaluation strategy for a feature flag."""

    BOOLEAN = "boolean"
    """Simple on/off control."""

    PERCENTAGE = "percentage"
    """Percentage-based gradual rollout (0-100)."""

    USER_LIST = "user_list"
    """Enabled for an explicit list of user IDs."""

    USER_ATTRIBUTE = "user_attribute"
    """Enabled when user attributes match all required key/value pairs."""

    TIME_BASED = "time_based"
    """Active within an optional [start_time, end_time] window."""

    VARIANT = "variant"
    """A/B test or multi-variant rollout with weighted variants."""


# Value of a flag evaluation — boolean or a variant name.
FlagValue = bool | str


@dataclass
class Flag:
    """Full definition of a feature flag including its evaluation strategy."""

    name: str
    """Unique flag identifier."""

    type: FlagType = FlagType.BOOLEAN
    """Evaluation strategy; defaults to BOOLEAN."""

    enabled: bool = True
    """Master switch — if False the flag is always off regardless of type."""

    description: str = ""
    """Human-readable description."""

    # PERCENTAGE type
    percentage: int = 0
    """Rollout percentage (0-100), used when type is PERCENTAGE."""

    # USER_LIST type
    user_list: list[str] = field(default_factory=list)
    """Explicit list of user IDs to enable, used when type is USER_LIST."""

    # USER_ATTRIBUTE type
    user_attributes: dict[str, Any] = field(default_factory=dict)
    """Required user attribute key/value pairs, used when type is USER_ATTRIBUTE."""

    # TIME_BASED type
    start_time: datetime | None = None
    """Window start; None means no lower bound."""

    end_time: datetime | None = None
    """Window end; None means no upper bound."""

    # VARIANT type
    variants: dict[str, int] = field(default_factory=dict)
    """Variant name → weight mapping; weights must sum to 100."""

    default_variant: str = ""
    """Variant returned when no user context is available."""

    # Generic metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.type == FlagType.PERCENTAGE and not (0 <= self.percentage <= 100):
            raise ValueError(
                f"Percentage must be between 0 and 100, got {self.percentage}",
            )
        if self.type == FlagType.VARIANT and self.variants:
            total = sum(self.variants.values())
            if total != 100:
                raise ValueError(
                    f"Variant weights must sum to 100, got {total}",
                )


@dataclass
class FlagContext:
    """Evaluation context passed alongside a flag name.

    Providers use the attributes here to resolve percentage rollouts, user
    lists, attribute rules, and variant assignments deterministically.
    """

    user_id: str | None = None
    user_attributes: dict[str, Any] | None = None
    session_id: str | None = None
    request_id: str | None = None
    timestamp: float | None = None
    custom: dict[str, Any] | None = None

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Return an attribute from user_attributes or custom, or default.

        Checks user_attributes first, then custom, then returns default.
        """
        if self.user_attributes and key in self.user_attributes:
            return self.user_attributes[key]
        if self.custom and key in self.custom:
            return self.custom[key]
        return default

    def as_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for cache key computation."""
        return {
            "user_id": self.user_id,
            "user_attributes": self.user_attributes,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "custom": self.custom,
        }

    def context_hash(self) -> str:
        """Return a deterministic 12-char hex hash of the non-empty context fields."""
        filtered = {k: v for k, v in self.as_dict().items() if v not in (None, {}, [])}
        if not filtered:
            return ""
        ctx_str = dumps_str(filtered, sort_keys=True)
        return hashlib.sha256(ctx_str.encode()).hexdigest()[:12]


@dataclass
class FlagEvaluation:
    """Result of evaluating a feature flag for a given context.

    ``enabled`` is the boolean result; ``value`` holds the full evaluation
    value — a bool for boolean/percentage/list/attribute/time flags, or a
    variant name string for VARIANT flags.
    """

    flag_name: str
    enabled: bool
    reason: str
    value: FlagValue | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.value is None:
            self.value = self.enabled


__all__ = [
    "Flag",
    "FlagContext",
    "FlagEvaluation",
    "FlagType",
    "FlagValue",
]
