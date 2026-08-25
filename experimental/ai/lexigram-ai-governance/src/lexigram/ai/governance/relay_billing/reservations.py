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

from lexigram.ai.governance.budget import SlidingWindowCounter
from lexigram.ai.governance.relay_billing._reservation_dimensions import (
    DEFAULT_WINDOW_SECONDS,
    RELAY_DIMENSIONS,
    RelayReservationLimits,
    RelayScopeLimit,
    estimate_prompt_tokens,
    requested_max_output_tokens,
    scope_keys,
)
from lexigram.contracts.ai.governance import (
    RelayBillingError,
    RelayUsageReservation,
    RelayUsageScope,
    invalid_usage,
    quota_exhausted,
    reservation_expired,
)
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.identity import ambient as identity
from lexigram.logging import get_logger
from lexigram.primitives import clock

logger = get_logger(__name__)

__all__ = [
    "DEFAULT_RESERVATION_TTL",
    "DEFAULT_WINDOW_SECONDS",
    "RelayQuotaEntry",
    "RelayQuotaSnapshot",
    "RelayReservationLimits",
    "RelayReservationManager",
    "RelayScopeLimit",
    "estimate_prompt_tokens",
    "requested_max_output_tokens",
]

DEFAULT_RESERVATION_TTL = 60.0


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


@dataclass(frozen=True, slots=True)
class RelayQuotaEntry:
    """One dimension's quota configuration and current usage.

    Attributes:
        dimension: Scope dimension the entry applies to.
        value: Scope values currently tracked on the dimension.
        max_tokens: Configured token limit for the window.
        max_charge: Configured charge limit for the window.
        window_seconds: Sliding window size in seconds.
        used_tokens: Tokens currently held by live reservations.
        used_charge: Charge currently held by live reservations.
    """

    dimension: str
    value: str
    max_tokens: int
    max_charge: Decimal
    window_seconds: float
    used_tokens: int
    used_charge: Decimal

    def remaining_tokens(self) -> int:
        """Return tokens still available in the window (never negative)."""
        return max(0, self.max_tokens - self.used_tokens)

    def remaining_charge(self) -> Decimal:
        """Return charge still available in the window (never negative)."""
        return max(Decimal("0"), self.max_charge - self.used_charge)


@dataclass(frozen=True, slots=True)
class RelayQuotaSnapshot:
    """Read-only quota usage per configured scope dimension.

    Attributes:
        tenant: Tenant-dimension quota entry, when limits are configured.
        account: Account-dimension quota entry, when limits are configured.
        user: User-dimension quota entry, when limits are configured.
        model: Model-dimension quota entry, when limits are configured.
        provider: Provider-dimension quota entry, when limits are configured.
        channel: Channel-dimension quota entry, when limits are configured.
    """

    tenant: RelayQuotaEntry | None = None
    account: RelayQuotaEntry | None = None
    user: RelayQuotaEntry | None = None
    model: RelayQuotaEntry | None = None
    provider: RelayQuotaEntry | None = None
    channel: RelayQuotaEntry | None = None


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
            for key in scope_keys(self._limits, scope):
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

    async def quota_snapshot(self) -> RelayQuotaSnapshot:
        """Report configured limits and current usage per dimension.

        Expired reservations are released first so the snapshot reflects
        live capacity only.  Dimensions without a configured limit never
        appear in the snapshot.

        Returns:
            Per-dimension quota entries aggregating every tracked window
            value; ``None`` for unconfigured dimensions.
        """
        async with self._lock:
            await self._release_expired(clock.now())
            entries: dict[str, RelayQuotaEntry] = {}
            for dimension in RELAY_DIMENSIONS:
                limit = getattr(self._limits, dimension)
                if limit is None:
                    continue
                prefix = f"{dimension}:"
                keys = sorted(
                    key for key in self._token_windows if key.startswith(prefix)
                )
                if not keys:
                    continue
                used_tokens = 0
                used_charge = Decimal("0")
                for key in keys:
                    used_tokens += int(await self._token_window(key).total())
                    used_charge += Decimal(str(await self._charge_window(key).total()))
                entries[dimension] = RelayQuotaEntry(
                    dimension=dimension,
                    value=", ".join(key.partition(":")[2] for key in keys),
                    max_tokens=limit.max_tokens,
                    max_charge=limit.max_charge,
                    window_seconds=limit.window_seconds,
                    used_tokens=used_tokens,
                    used_charge=used_charge,
                )
            return RelayQuotaSnapshot(
                tenant=entries.get("tenant"),
                account=entries.get("account"),
                user=entries.get("user"),
                model=entries.get("model"),
                provider=entries.get("provider"),
                channel=entries.get("channel"),
            )

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
