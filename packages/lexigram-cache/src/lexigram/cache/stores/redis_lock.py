"""Redis lock store implementation"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
import time
from types import EllipsisType
from typing import (
    TYPE_CHECKING,
    Any,
    cast,
)
from uuid import uuid4

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable

logger = get_logger(__name__)

try:
    import redis as _redis
    from redis import RedisError

    redis = _redis
    HAS_REDIS = True
except ImportError:
    redis = None  # type: ignore[assignment]
    RedisError = Exception  # type: ignore[misc,assignment]
    HAS_REDIS = False


# Import component exceptions lazily at runtime to avoid circular import issues during module import
# (they are imported inside methods where they are used)


class RedisLockStore:
    """Redis implementation of LockStore with owner validation.

    Locks are stored as the value of the key and contain a `lock_id` of the
    form `<owner>:<uuid>`. Release and extend operations are executed via
    Lua scripts that compare-and-delete or compare-and-expire atomically.
    """

    # Lua scripts
    LUA_RELEASE_LOCK = """
        local cur = redis.call("GET", KEYS[1])
        if cur == false then
            return -1
        elseif cur == ARGV[1] then
            redis.call("DEL", KEYS[1])
            return 1
        else
            return 0
        end
        """

    LUA_EXTEND_LOCK = """
        local cur = redis.call("GET", KEYS[1])
        if cur == false then
            return -1
        elseif cur == ARGV[1] then
            redis.call("PEXPIRE", KEYS[1], ARGV[2])
            return 1
        else
            return 0
        end
        """

    def __init__(self, url: str = "", prefix: str = "", client: Any | None = None):
        self.url = url
        self.prefix = prefix
        self._client: Any | None = client

    async def _get_client(self) -> Any:
        """Lazy client initialization"""
        if self._client is not None:
            return self._client
        if not HAS_REDIS:
            raise ImportError(
                "Redis driver is required for Redis-based components. Install with: pip install redis>=4.6.0",
            )
        if self._client is None:
            if redis is None:
                raise RuntimeError("Redis module not available")
            # redis.from_url is untyped in our environment; ignore the untyped-call here
            self._client = redis.from_url(self.url, decode_responses=True)
        return self._client

    def _key(self, key: str) -> str:
        """Apply prefix to key"""
        return f"{self.prefix}{key}" if self.prefix else key

    async def acquire(
        self,
        resource: str,
        ttl: int = 30,
        owner: str | EllipsisType = ...,
    ) -> str | None:
        """Acquire a lock.

        Args:
            resource: The resource to lock.
            ttl: Lock TTL in seconds.
            owner: Owner identifier (required).

        Returns:
            lock_id (str) on success, None on failure.
        """
        if owner is ...:
            raise ValueError(
                "owner parameter is required - use a string identifier for the lock owner"
            )

        client = await self._get_client()
        ttl_ms = int(ttl * 1000)

        logger.debug(
            "acquire: resource=%s owner=%s ttl=%sms",
            resource,
            owner,
            ttl_ms,
            extra={"resource": resource, "owner": owner, "ttl_ms": ttl_ms},
        )

        owner_part = owner
        lock_id = f"{owner_part}:{uuid4().hex}"

        result = await cast(
            "Awaitable[Any]",
            client.set(self._key(f"lock:{resource}"), lock_id, px=ttl_ms, nx=True),
        )

        if result is True:
            logger.info(
                "acquire: lock acquired resource=%s lock_id=%s",
                resource,
                lock_id,
            )
            return lock_id

        logger.info("acquire: lock failed resource=%s owner=%s", resource, owner)
        return None

    async def release(self, resource: str, lock_id: str) -> None:
        """Release a lock only if `lock_id` matches the current owner.

        Raises:
            LockNotHeldError: if the lock does not exist
            LockOwnershipError: if the lock is held by someone else
        """
        client = await self._get_client()
        res = await cast(
            "Awaitable[int]",
            client.eval(
                self.LUA_RELEASE_LOCK,
                1,
                self._key(f"lock:{resource}"),
                lock_id,
            ),
        )

        if res == -1:
            logger.warning(
                "release: lock not held resource=%s lock_id=%s",
                resource,
                lock_id,
            )
            from lexigram.contracts.exceptions.components import (
                LockNotHeldError,
            )

            raise LockNotHeldError(resource)
        if res == 0:
            logger.warning(
                "release: ownership mismatch resource=%s lock_id=%s",
                resource,
                lock_id,
            )
            from lexigram.contracts.exceptions.components import (
                LockNotHeldError as LockOwnershipError,  # type: ignore[attr-defined,unused-ignore]
            )

            raise LockOwnershipError(resource)

        logger.info("release: lock released resource=%s lock_id=%s", resource, lock_id)
        # res == 1 => success

    async def extend(self, resource: str, lock_id: str, ttl: int) -> None:
        """Extend TTL of a lock only if `lock_id` matches the current owner.

        Raises:
            LockNotHeldError: if the lock does not exist
            LockOwnershipError: if the lock is held by someone else
        """
        client = await self._get_client()
        ttl_ms = int(ttl * 1000)
        res = await cast(
            "Awaitable[int]",
            client.eval(
                self.LUA_EXTEND_LOCK,
                1,
                self._key(f"lock:{resource}"),
                lock_id,
                ttl_ms,
            ),
        )

        if res == -1:
            logger.warning(
                "extend: lock not held resource=%s lock_id=%s",
                resource,
                lock_id,
            )
            from lexigram.contracts.exceptions.components import (
                LockNotHeldError,
            )

            raise LockNotHeldError(resource)
        if res == 0:
            logger.warning(
                "extend: ownership mismatch resource=%s lock_id=%s",
                resource,
                lock_id,
            )
            from lexigram.contracts.exceptions.components import (
                LockNotHeldError as LockOwnershipError,  # type: ignore[attr-defined,unused-ignore]
            )

            raise LockOwnershipError(resource)

        logger.info(
            "extend: lock extended resource=%s lock_id=%s ttl_ms=%s",
            resource,
            lock_id,
            ttl_ms,
        )

    async def is_locked(self, key: str) -> bool:
        """Check if a key is locked"""
        client = await self._get_client()
        res = await client.exists(self._key(f"lock:{key}"))
        exists = cast("int", res)
        logger.debug("is_locked: key=%s exists=%s", key, exists)
        return exists > 0

    @asynccontextmanager
    async def locked(
        self,
        resource: str,
        ttl: int = 30,
        owner: str | None = None,
    ) -> Any:
        """Async context manager that acquires a lock and releases it on exit.

        Yields the `lock_id` string.
        """
        lock_id = await self.acquire(resource, ttl=ttl, owner=owner)  # type: ignore[arg-type]
        if lock_id is None:
            logger.info(
                "locked: failed to acquire resource=%s owner=%s",
                resource,
                owner,
            )
            from lexigram.contracts.exceptions.components import (
                LockAcquisitionError,
            )

            raise LockAcquisitionError(resource, "Resource is already locked")

        logger.info("locked: acquired resource=%s lock_id=%s", resource, lock_id)
        try:
            yield lock_id
        finally:
            try:
                await self.release(resource, lock_id)
                logger.info(
                    "locked: released resource=%s lock_id=%s",
                    resource,
                    lock_id,
                )
            except (ConnectionError, OSError, TimeoutError, RuntimeError) as exc:
                # Import lazily to avoid circular imports at module import time
                from lexigram.contracts.exceptions.components import (
                    LockNotHeldError,
                )

                if isinstance(exc, LockNotHeldError):
                    logger.warning(
                        "locked: attempted release but lock not held resource=%s lock_id=%s",
                        resource,
                        lock_id,
                    )
                else:
                    raise

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check the health of the lock store"""
        start_time = time.monotonic()
        try:
            client = await self._get_client()

            await cast("Awaitable[Any]", client.ping())
            duration_ms = (time.monotonic() - start_time) * 1000
            return HealthCheckResult(
                component="lock_store",
                status=HealthStatus.HEALTHY,
                message="Redis lock store is healthy",
                details={
                    "driver": "redis",
                    "url": self.url,
                },
                duration_ms=duration_ms,
                checked_at=datetime.now(UTC),
            )
        except (ConnectionError, OSError, TimeoutError, RuntimeError) as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.exception("Redis lock store health check failed")
            return HealthCheckResult(
                component="lock_store",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis lock store unhealthy: {e!s}",
                error=str(e),
                details={
                    "driver": "redis",
                    "url": self.url,
                },
                duration_ms=duration_ms,
                checked_at=datetime.now(UTC),
            )
