from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class FallbackStrategy(StrEnum):
    """Strategies for fallback execution."""

    RETRY = "retry"
    CIRCUIT_BREAKER = "circuit_breaker"
    DEGRADATION = "degradation"
    ALTERNATIVE = "alternative"


@dataclass
class DegradationConfig:
    """Configuration for degradation fallback strategy."""

    degraded_result: Any = None
    log_level: int | None = None
