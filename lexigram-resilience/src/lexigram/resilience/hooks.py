"""Root hook payload surface for lexigram-resilience.

Defines canonical payload dataclasses for resilience-pattern hook points.
Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "CircuitClosedHook",
    "CircuitOpenedHook",
    "RetryAttemptedHook",
]


@dataclass(frozen=True, kw_only=True)
class CircuitOpenedHook:
    """Payload fired when a circuit breaker transitions to the OPEN state.

    Attributes:
        circuit_name: Name of the circuit breaker that opened.
    """

    circuit_name: str


@dataclass(frozen=True, kw_only=True)
class CircuitClosedHook:
    """Payload fired when a circuit breaker transitions back to the CLOSED state.

    Attributes:
        circuit_name: Name of the circuit breaker that closed.
    """

    circuit_name: str


@dataclass(frozen=True, kw_only=True)
class RetryAttemptedHook:
    """Payload fired on each retry attempt after an operation failure.

    Attributes:
        operation: Name or label of the operation being retried.
        attempt: Attempt number (1-based).
    """

    operation: str
    attempt: int
