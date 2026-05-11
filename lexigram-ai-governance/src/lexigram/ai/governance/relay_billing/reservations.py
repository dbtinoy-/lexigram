"""Relay reservation and quota admission.

Implements in-memory admission control for relay requests: an async
``RelayReservationManager`` holds sliding token/charge windows per
configured scope dimension (tenant, account, user, model, provider,
channel) and reserves capacity before upstream admission.  The reserve
operation is atomic across every applicable scope under a single async
lock, so concurrent requests cannot oversubscribe a configured limit.

Prompt estimation for the reservation uses an injected token counter
when available; otherwise it falls back to the explicit character
estimate used by the LLM pricing conventions (~4 chars per token).
Requested max output tokens are included only in the admission
reservation and are never copied into actual usage.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from lexigram.ai.governance.budget import SlidingWindowCounter
from lexigram.contracts.ai.governance import (
    RelayBillingError,
    RelayUsageReservation,
    RelayUsageScope,
    invalid_usage,
    quota_exhausted,
    reservation_expired,
)
from lexigram.contracts.ai.relay import (
    ClaudeRequest,
    GeminiRequest,
    OpenAIChatRequest,
    RelayRequestPayload,
    ResponsesRequest,
)
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.identity import ambient as identity
from lexigram.logging import get_logger
from lexigram.primitives import clock
from lexigram.serialization import dumps_str

if TYPE_CHECKING:
    from lexigram.contracts.ai.llm import TokenCounterProtocol

logger = get_logger(__name__)

__all__ = [
    "DEFAULT_RESERVATION_TTL",
    "DEFAULT_WINDOW_SECONDS",
    "RelayReservationLimits",
    "RelayReservationManager",
    "RelayScopeLimit",
    "estimate_prompt_tokens",
    "requested_max_output_tokens",
]

RELAY_DIMENSIONS = ("tenant", "account", "user", "model", "provider", "channel")
DEFAULT_WINDOW_SECONDS = 60.0
DEFAULT_RESERVATION_TTL = 60.0
_CHARS_PER_TOKEN = 4


@dataclass(frozen=True, slots=True)
class RelayScopeLimit:
    """Admission quota for one scope dimension.

    Attributes:
        max_tokens: Maximum tokens admitted in the sliding window.
        max_charge: Maximum charge admitted in the sliding window.
        window_seconds: Sliding window size in seconds.
    """

    max_tokens: int
    max_charge: Decimal
    window_seconds: float = DEFAULT_WINDOW_SECONDS

    def __post_init__(self) -> None:
        """Reject negative token/charge limits or a non-positive window."""
        if self.max_tokens < 0:
            raise ValueError("max_tokens must be non-negative")
        if self.max_charge < 0:
            raise ValueError("max_charge must be non-negative")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass(frozen=True, slots=True)
class RelayReservationLimits:
    """Configured per-dimension admission limits.

    Attributes:
        tenant: Tenant-scope limit, when enforced.
        account: Account-scope limit, when enforced.
        user: User-scope limit, when enforced.
        model: Model-scope limit, when enforced.
        provider: Provider-scope limit, when enforced.
        channel: Channel-scope limit, when enforced.
    """

    tenant: RelayScopeLimit | None = None
    account: RelayScopeLimit | None = None
    user: RelayScopeLimit | None = None
    model: RelayScopeLimit | None = None
    provider: RelayScopeLimit | None = None
    channel: RelayScopeLimit | None = None


@dataclass(frozen=True, slots=True)
class _ReservationState:
    """In-memory reservation bookkeeping.

    Attributes:
        reservation: The public reservation value.
        window_keys: Sliding-window keys amounts were reserved on.
        expires_at: Reservation expiry instant (timezone-aware).
    """

    reservation: RelayUsageReservation
    window_keys: tuple[str, ...]
    expires_at: datetime


def _payload_text(payload: RelayRequestPayload) -> str:
    """Serialize a request payload to a JSON text for estimation."""
    return dumps_str(payload.to_dict())


def estimate_prompt_tokens(
    payload: RelayRequestPayload,
    token_counter: TokenCounterProtocol | None = None,
) -> int:
    """Estimate the prompt token count for a request payload.

    Args:
        payload: Relay request payload to estimate.
        token_counter: Optional model-aware token counter; when provided
            it counts the serialized payload, otherwise the character
            estimate (~4 chars per token) is used.

    Returns:
        A non-negative, admission-only token estimate.
    """
    text = _payload_text(payload)
    if token_counter is not None:
        return max(0, int(token_counter.count(text)))
    return max(1, len(text) // _CHARS_PER_TOKEN)


def requested_max_output_tokens(payload: RelayRequestPayload) -> int:
    """Return the requested max output tokens, or 0 when not set.

    Args:
        payload: Relay request payload to inspect.

    Returns:
        The requested output budget, or 0 when the request does not
        carry one.
    """
    if isinstance(payload, OpenAIChatRequest):
        value = payload.max_completion_tokens or payload.max_tokens
        return value or 0
    if isinstance(payload, ResponsesRequest):
        return payload.max_output_tokens or 0
    if isinstance(payload, ClaudeRequest):
        return payload.max_tokens
    if isinstance(payload, GeminiRequest):
        value = payload.generation_config.get("maxOutputTokens")
        if value is None:
            value = payload.generation_config.get("max_output_tokens")
        return int(value) if value is not None else 0
    return 0


class RelayReservationManager:
    """In-memory admission reservations across configured scope quotas.

    Reservations hold estimated token and charge amounts in sliding
    windows so concurrent requests cannot oversubscribe a configured
    limit.  The :meth:`reserve` operation is atomic across every
    applicable scope under one async lock, so concurrent requests cannot
    double-spend capacity.  Expired reservations are released before a
    new admission check; releasing is idempotent and harmless.

    Args:
        limits: Per-dimension quota configuration.
        ttl_seconds: Default reservation lifetime in seconds.
    """

    def __init__(
        self,
        limits: RelayReservationLimits | None = None,
        *,
        ttl_seconds: float = DEFAULT_RESERVATION_TTL,
    ) -> None:
        self._limits = limits or RelayReservationLimits()
        self._ttl_seconds = ttl_seconds
        self._token_windows: dict[str, SlidingWindowCounter] = {}
        self._charge_windows: dict[str, SlidingWindowCounter] = {}
        self._reservations: dict[str, _ReservationState] = {}
        self._started: set[str] = set()
        self._lock = asyncio.Lock()

    def _token_window(self, key: str) -> SlidingWindowCounter:
        """Return the token window for *key*, creating it lazily."""
        window = self._token_windows.get(key)
        if window is None:
            window = SlidingWindowCounter()
            self._token_windows[key] = window
        return window

    def _charge_window(self, key: str) -> SlidingWindowCounter:
        """Return the charge window for *key*, creating it lazily."""
        window = self._charge_windows.get(key)
        if window is None:
            window = SlidingWindowCounter()
            self._charge_windows[key] = window
        return window

    def _scope_value(self, scope: RelayUsageScope, dimension: str) -> str:
        """Return the value of a dimension in *scope* (``""`` if unset)."""
        if dimension == "tenant":
            return scope.tenant_id
        if dimension == "model":
            return scope.model
        if dimension == "provider":
            return scope.provider
        if dimension == "channel":
            return scope.channel
        if dimension == "account":
            return scope.account_id or ""
        return scope.user_id or ""

    def _scope_keys(self, scope: RelayUsageScope) -> list[str]:
        """Collect internal window keys for the configured scope.

        Args:
            scope: The scope to map onto configured dimensions.

        Returns:
            Window keys ``"<dim>:<value>"`` for every configured
            dimension the scope carries a value for.
        """
        keys: list[str] = []
        for dimension in RELAY_DIMENSIONS:
            limit = getattr(self._limits, dimension)
            if limit is None:
                continue
            value = self._scope_value(scope, dimension)
            if not value:
                logger.debug(
                    "relay_reservation_scope_empty",
                    dimension=dimension,
                    tenant_id=scope.tenant_id,
                )
                continue
            keys.append(f"{dimension}:{value}")
        return keys

    async def reserve(
        self,
        request_id: str,
        scope: RelayUsageScope,
        estimated_tokens: int,
        estimated_charge: Decimal,
        *,
        ttl_seconds: float | None = None,
    ) -> Result[RelayUsageReservation, RelayBillingError]:
        """Atomically reserve capacity across every applicable scope.

        Args:
            request_id: Gateway request identifier for the reservation.
            scope: Accounting scope of the request.
            estimated_tokens: Prompt estimate used for admission only,
                including requested max output tokens folded in by the
                caller.
            estimated_charge: Maximum charge the reservation covers.
            ttl_seconds: Reservation lifetime override; defaults to the
                manager's configured TTL.

        Returns:
            ``Ok(reservation)`` when every applicable scope has room,
            otherwise ``Err`` with code ``invalid_usage`` or
            ``quota_exhausted``.
        """
        if estimated_tokens < 0:
            return Err(
                invalid_usage(
                    message="estimated_tokens must be non-negative",
                    request_id=request_id,
                    tenant_id=scope.tenant_id,
                )
            )
        if estimated_charge < 0:
            return Err(
                invalid_usage(
                    message="estimated_charge must be non-negative",
                    request_id=request_id,
                    tenant_id=scope.tenant_id,
                )
            )
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
        if ttl <= 0:
            return Err(
                invalid_usage(
                    message="reservation TTL must be positive",
                    request_id=request_id,
                    tenant_id=scope.tenant_id,
                )
            )

        async with self._lock:
            now = clock.now()
            await self._release_expired(now)

            window_keys: list[str] = []
            for key in self._scope_keys(scope):
                dimension, _, _ = key.partition(":")
                limit = getattr(self._limits, dimension)
                if limit is None:
                    continue
                token_total = await self._token_window(key).total()
                if token_total + estimated_tokens > limit.max_tokens:
                    return Err(
                        quota_exhausted(
                            message=(
                                f"{dimension} token quota {limit.max_tokens} "
                                f"exceeded ({token_total} used + {estimated_tokens})"
                            ),
                            request_id=request_id,
                            tenant_id=scope.tenant_id,
                        )
                    )
                charge_total = await self._charge_window(key).total()
                if charge_total + float(estimated_charge) > float(limit.max_charge):
                    return Err(
                        quota_exhausted(
                            message=(
                                f"{dimension} credit quota {limit.max_charge} "
                                f"exceeded ({charge_total} used)"
                            ),
                            request_id=request_id,
                            tenant_id=scope.tenant_id,
                        )
                    )
                window_keys.append(key)

            reservation_id = identity.new_uuid()
            expires_at = now + timedelta(seconds=ttl)
            reservation = RelayUsageReservation(
                reservation_id=reservation_id,
                request_id=request_id,
                estimated_tokens=estimated_tokens,
                estimated_charge=estimated_charge,
                expires_at=expires_at,
            )
            for key in window_keys:
                await self._token_window(key).reserve(
                    reservation_id, float(estimated_tokens)
                )
                await self._charge_window(key).reserve(
                    reservation_id, float(estimated_charge)
                )
            self._reservations[reservation_id] = _ReservationState(
                reservation=reservation,
                window_keys=tuple(window_keys),
                expires_at=expires_at,
            )
            logger.info(
                "relay_reservation_created",
                reservation_id=reservation_id,
                request_id=request_id,
                estimated_tokens=estimated_tokens,
                estimated_charge=str(estimated_charge),
            )
            return Ok(reservation)

    async def mark_started(self, reservation_id: str) -> None:
        """Record that the upstream attempt started for a reservation.

        A reservation marked started may be settled even after expiry.

        Args:
            reservation_id: Reservation identifier.
        """
        async with self._lock:
            self._started.add(reservation_id)

    async def release(self, reservation_id: str) -> None:
        """Release a reservation and its reserved capacity.

        Idempotent and harmless for unknown reservation IDs.

        Args:
            reservation_id: Reservation identifier.
        """
        async with self._lock:
            await self._release_locked(reservation_id)

    async def settle(self, reservation_id: str) -> Result[None, RelayBillingError]:
        """Settle a reservation exactly once, freeing its capacity.

        A reservation cannot be settled after expiry unless the upstream
        attempt was marked started via :meth:`mark_started`.  Actual
        usage is recorded separately by the billing service.

        Args:
            reservation_id: Reservation identifier.

        Returns:
            Ok(None) on settlement, or an Err of code
            ``reservation_expired`` when it expired before starting.
        """
        async with self._lock:
            state = self._reservations.get(reservation_id)
            if state is None:
                return Ok(None)
            now = clock.now()
            if state.expires_at <= now and reservation_id not in self._started:
                await self._release_locked(reservation_id)
                return Err(
                    reservation_expired(
                        message="reservation expired before starting",
                        request_id=state.reservation.request_id,
                    )
                )
            for key in state.window_keys:
                await self._token_window(key).release_reservation(reservation_id)
                await self._charge_window(key).release_reservation(reservation_id)
            self._reservations.pop(reservation_id, None)
            self._started.discard(reservation_id)
            logger.info("relay_reservation_settled", reservation_id=reservation_id)
            return Ok(None)

    async def _release_expired(self, now: datetime) -> None:
        """Release every reservation that expired at or before *now*."""
        for reservation_id, state in list(self._reservations.items()):
            if state.expires_at <= now:
                await self._release_locked(reservation_id)

    async def _release_locked(self, reservation_id: str) -> None:
        """Release a reservation assuming the manager lock is held."""
        state = self._reservations.pop(reservation_id, None)
        if state is None:
            return
        for key in state.window_keys:
            await self._token_window(key).release_reservation(reservation_id)
            await self._charge_window(key).release_reservation(reservation_id)
        self._started.discard(reservation_id)
        logger.debug("relay_reservation_released", reservation_id=reservation_id)
