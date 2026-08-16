"""Circuit breaker backend protocol and implementations.

This module provides backend support for circuit breaker state,
enabling distributed/multi-process deployments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from lexigram import serialization as json
from lexigram.resilience.circuit.breaker import CircuitState

if TYPE_CHECKING:
    from lexigram.contracts import StateStoreProtocol


@dataclass
class CircuitBreakerState:
    """Serialized circuit breaker state for distributed storage."""

    name: str
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: float | None
    last_success_time: float | None
    last_state_change: float


class CircuitBreakerBackend(Protocol):
    """Protocol for circuit breaker state backends.

    Implement this to enable distributed circuit breakers
    across multiple processes or containers.
    """

    async def get_state(self, name: str) -> CircuitBreakerState | None:
        """Get circuit breaker state by name.

        Args:
            name: Circuit breaker name.

        Returns:
            State if exists, None otherwise.
        """
        ...

    async def set_state(self, name: str, state: CircuitBreakerState) -> None:
        """Set circuit breaker state.

        Args:
            name: Circuit breaker name.
            state: State to store.
        """
        ...

    async def delete_state(self, name: str) -> None:
        """Delete circuit breaker state.

        Args:
            name: Circuit breaker name.
        """
        ...


class InMemoryCircuitBreakerBackend:
    """In-memory backend for circuit breaker state.

    Suitable for single-process deployments or testing.
    Note: Does not work across multiple processes/containers.
    """

    def __init__(self) -> None:
        self._states: dict[str, CircuitBreakerState] = {}

    async def get_state(self, name: str) -> CircuitBreakerState | None:
        """Get circuit breaker state by name."""
        return self._states.get(name)

    async def set_state(self, name: str, state: CircuitBreakerState) -> None:
        """Set circuit breaker state."""
        self._states[name] = state

    async def delete_state(self, name: str) -> None:
        """Delete circuit breaker state."""
        self._states.pop(name, None)


_STATE_PREFIX = "circuit_breaker:"


class DistributedCircuitBreakerBackend:
    """Distributed circuit breaker backend backed by a :class:`lexigram.contracts.StateStoreProtocol`.

    Stores serialized :class:`CircuitBreakerState` as JSON so that all
    processes sharing the same ``StateStoreProtocol`` see a consistent view of
    each circuit breaker's state.

    Example::

        from lexigram.contracts import StateStoreProtocol
        from lexigram.resilience.circuit.backend import DistributedCircuitBreakerBackend

        backend = DistributedCircuitBreakerBackend(store=state_store)
        breaker = CircuitBreaker(name="payments", backend=backend)
    """

    def __init__(self, store: StateStoreProtocol, ttl: int = 3600) -> None:
        """Initialise the backend.

        Args:
            store: A :class:`~lexigram.contracts.StateStoreProtocol` implementation
                (e.g. the Redis-backed state store from ``lexigram-sql``).
            ttl: Time-to-live (seconds) for each stored state entry.
                Defaults to 1 hour, ensuring stale entries are eventually
                cleaned up even if :meth:`delete_state` is never called.
        """
        self._store = store
        self._ttl = ttl

    def _key(self, name: str) -> str:
        return f"{_STATE_PREFIX}{name}"

    async def get_state(self, name: str) -> CircuitBreakerState | None:
        """Fetch circuit breaker state from the distributed store.

        Args:
            name: Circuit breaker name.

        Returns:
            Deserialized state, or ``None`` if not found.
        """
        raw = await self._store.get(self._key(name))
        if raw is None:
            return None
        data: dict = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
        return CircuitBreakerState(
            name=data["name"],
            state=CircuitState(data["state"]),
            failure_count=data["failure_count"],
            success_count=data["success_count"],
            last_failure_time=data.get("last_failure_time"),
            last_success_time=data.get("last_success_time"),
            last_state_change=data["last_state_change"],
        )

    async def set_state(self, name: str, state: CircuitBreakerState) -> None:
        """Persist circuit breaker state to the distributed store.

        Args:
            name: Circuit breaker name.
            state: State to store.
        """
        data = {
            "name": state.name,
            "state": state.state.value,
            "failure_count": state.failure_count,
            "success_count": state.success_count,
            "last_failure_time": state.last_failure_time,
            "last_success_time": state.last_success_time,
            "last_state_change": state.last_state_change,
        }
        await self._store.set(self._key(name), json.dumps(data), self._ttl)

    async def delete_state(self, name: str) -> None:
        """Remove circuit breaker state from the distributed store.

        Args:
            name: Circuit breaker name.
        """
        await self._store.delete(self._key(name))


__all__ = [
    "CircuitBreakerBackend",
    "CircuitBreakerState",
    "CircuitState",
    "DistributedCircuitBreakerBackend",
    "InMemoryCircuitBreakerBackend",
]
