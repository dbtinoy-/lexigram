"""Admin login attempt service — IP rate limiting and account lockout."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib

from lexigram.admin.auth.errors import AccountLockedError, RateLimitExceededError
from lexigram.admin.auth.protocols import (
    AdminAccountLockoutStoreProtocol,
    AdminLoginAttemptStoreProtocol,
)
from lexigram.admin.auth.types import AdminLockoutStatus, AdminLoginAttempt
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class AdminLoginAttemptService:
    """Manages IP rate limiting and progressive account lockout for admin auth.

    IP rate limiting uses an optional CacheBackendProtocol. If cache is
    unavailable (None), rate limiting is gracefully skipped (fail open).
    Account lockout is DB-persisted and survives restarts.
    """

    def __init__(
        self,
        attempt_store: AdminLoginAttemptStoreProtocol,
        lockout_store: AdminAccountLockoutStoreProtocol,
        cache: CacheBackendProtocol | None = None,
        ip_rate_limit_enabled: bool = True,
        ip_limit_per_minute: int = 10,
        ip_limit_per_15_minutes: int = 30,
        ip_limit_per_hour: int = 60,
        lockout_thresholds: list[tuple[int, int]] | None = None,
        permanent_lockout_threshold: int = 50,
    ) -> None:
        """Initialize with stores and configuration.

        Args:
            attempt_store: Store for login attempt records.
            lockout_store: Store for account lockout records.
            cache: Optional cache backend for IP rate limiting.
            ip_rate_limit_enabled: Whether IP rate limiting is active.
            ip_limit_per_minute: Max failures per IP per minute.
            ip_limit_per_15_minutes: Max failures per IP per 15 minutes.
            ip_limit_per_hour: Max failures per IP per hour.
            lockout_thresholds: List of (failure_count, lockout_minutes) pairs.
                Defaults to [(5, 15), (10, 60), (15, 240), (20, 1440)].
            permanent_lockout_threshold: Failures before permanent lockout.
        """
        self._attempt_store = attempt_store
        self._lockout_store = lockout_store
        self._cache = cache
        self._ip_rate_limit_enabled = ip_rate_limit_enabled
        self._ip_limit_per_minute = ip_limit_per_minute
        self._ip_limit_per_15_minutes = ip_limit_per_15_minutes
        self._ip_limit_per_hour = ip_limit_per_hour
        self._lockout_thresholds = lockout_thresholds or [
            (5, 15),
            (10, 60),
            (15, 240),
            (20, 1440),
        ]
        self._permanent_lockout_threshold = permanent_lockout_threshold

    async def check_ip_rate_limit(self, ip_address: str) -> None:
        """Check if IP is rate-limited. Raises RateLimitExceededError if exceeded.

        Uses cache for fast lookups. Gracefully skips if cache is unavailable.

        Args:
            ip_address: Client IP address.

        Raises:
            RateLimitExceededError: When the IP exceeds any rate limit tier.
        """
        if not self._ip_rate_limit_enabled or self._cache is None:
            return

        # Hash IP to avoid PII in Redis KEYS output
        ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16]

        try:
            # Check three tiers using the DB-backed attempt store for accuracy
            # (Cache is used for hard blocks only — set by prior blocked requests)
            blocked_key = f"admin:blocked:ip:{ip_hash}"
            is_blocked = await self._cache.get(blocked_key)
            if is_blocked.is_ok() and is_blocked.unwrap():
                logger.warning("ip_rate_limit.hard_blocked", ip_hash=ip_hash)
                raise RateLimitExceededError(
                    "Too many failed login attempts from this IP. Please try again later.",
                    reason="rate_limit",
                )

            # Count recent failures from DB
            failures_1min = await self._attempt_store.count_recent_failures_by_ip(
                ip_address, 60
            )
            failures_15min = await self._attempt_store.count_recent_failures_by_ip(
                ip_address, 900
            )
            failures_1hr = await self._attempt_store.count_recent_failures_by_ip(
                ip_address, 3600
            )

            if failures_1min >= self._ip_limit_per_minute:
                # Set a 5-minute hard block in cache
                await self._cache.set(blocked_key, "1", ttl=300)
                logger.warning(
                    "ip_rate_limit.exceeded_minute",
                    ip_hash=ip_hash,
                    count=failures_1min,
                )
                raise RateLimitExceededError(
                    "Too many login attempts. Please wait 5 minutes before trying again.",
                    retry_after=300,
                    reason="rate_limit",
                )

            if failures_15min >= self._ip_limit_per_15_minutes:
                await self._cache.set(blocked_key, "1", ttl=900)
                logger.warning(
                    "ip_rate_limit.exceeded_15min",
                    ip_hash=ip_hash,
                    count=failures_15min,
                )
                raise RateLimitExceededError(
                    "Too many login attempts. Please wait 15 minutes before trying again.",
                    retry_after=900,
                    reason="rate_limit",
                )

            if failures_1hr >= self._ip_limit_per_hour:
                await self._cache.set(blocked_key, "1", ttl=3600)
                logger.warning(
                    "ip_rate_limit.exceeded_hour",
                    ip_hash=ip_hash,
                    count=failures_1hr,
                )
                raise RateLimitExceededError(
                    "Too many login attempts. Please try again in 1 hour.",
                    retry_after=3600,
                    reason="rate_limit",
                )

        except RateLimitExceededError:
            raise
        except Exception:  # noqa: BLE001
            # Cache is unavailable — fail open (never block auth due to cache failure)
            logger.warning("ip_rate_limit.cache_unavailable", ip_hash=ip_hash)

    async def check_account_lockout(self, email: str) -> None:
        """Check account lockout. Raises AccountLockedError if locked.

        Args:
            email: Email to check.

        Raises:
            AccountLockedError: When the account is locked.
        """
        lockout_info = await self._lockout_store.get_active_lockout(email)
        if lockout_info is None:
            return

        if lockout_info.status == AdminLockoutStatus.PERMANENT:
            raise AccountLockedError(
                "This account has been permanently locked. Please contact an administrator.",
                reason="lockout",
            )

        if lockout_info.status == AdminLockoutStatus.LOCKED:
            if lockout_info.unlock_at:
                retry_after = max(
                    0,
                    int((lockout_info.unlock_at - datetime.now(UTC)).total_seconds()),
                )
                raise AccountLockedError(
                    f"Account temporarily locked due to too many failed attempts. "
                    f"Please try again after {lockout_info.unlock_at.strftime('%H:%M UTC')}.",
                    unlock_at=lockout_info.unlock_at,
                    retry_after=retry_after,
                    reason="lockout",
                )
            raise AccountLockedError(
                "Account is temporarily locked. Please try again later.",
                reason="lockout",
            )

    async def record_attempt(
        self,
        email: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        failure_reason: str | None = None,
    ) -> None:
        """Record a login attempt and update lockout state on failure.

        On success, lockout counters are NOT cleared here — use clear_lockout().
        On failure, checks thresholds and creates/updates lockout record.

        Args:
            email: Email that attempted login.
            ip_address: Client IP.
            user_agent: Client user agent.
            success: Whether the attempt succeeded.
            failure_reason: Short failure code when success=False.
        """
        from datetime import timedelta
        import uuid

        attempt = AdminLoginAttempt(
            id=str(uuid.uuid4()),
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
            attempted_at=datetime.now(UTC),
        )
        await self._attempt_store.insert(attempt)

        if success:
            return

        # Count total consecutive failures to determine lockout level
        total_failures = await self._attempt_store.count_recent_failures(email, 86400)

        if total_failures >= self._permanent_lockout_threshold:
            await self._lockout_store.create_lockout(
                email=email,
                consecutive_failures=total_failures,
                unlock_at=None,
                is_permanent=True,
            )
            logger.warning(
                "account_lockout.permanent",
                email_hash=hashlib.sha256(email.encode()).hexdigest()[:8],
            )
            return

        # Find applicable lockout threshold
        lockout_minutes: int | None = None
        for threshold_failures, minutes in sorted(
            self._lockout_thresholds, reverse=True
        ):
            if total_failures >= threshold_failures:
                lockout_minutes = minutes
                break

        if lockout_minutes is not None:
            unlock_at = datetime.now(UTC) + timedelta(minutes=lockout_minutes)
            await self._lockout_store.create_lockout(
                email=email,
                consecutive_failures=total_failures,
                unlock_at=unlock_at,
                is_permanent=False,
            )
            logger.warning(
                "account_lockout.temporary",
                email_hash=hashlib.sha256(email.encode()).hexdigest()[:8],
                minutes=lockout_minutes,
                failures=total_failures,
            )

    async def clear_lockout(self, email: str) -> None:
        """Clear lockout and failure records on successful login.

        Args:
            email: Email to clear.
        """
        await self._lockout_store.clear_lockout(email)
        await self._attempt_store.clear_failures(email)
        logger.debug(
            "account_lockout.cleared",
            email_hash=hashlib.sha256(email.encode()).hexdigest()[:8],
        )


__all__ = ["AdminLoginAttemptService"]
