"""HTTP middleware for idempotency key header enforcement.

Intercepts HTTP requests carrying an ``Idempotency-Key`` header and, on a
cache hit for that key, returns the previously stored response without
executing the handler.  On a cache miss the handler runs normally and its
response is stored so that the next duplicate request receives the same reply.

The middleware delegates storage to the registered
:class:`~lexigram.contracts.core.idempotency.IdempotencyStoreProtocol` and is
intentionally framework-agnostic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram import serialization
from lexigram.contracts.exceptions.idempotency import IdempotencyStoreError
from lexigram.logging import get_logger
from lexigram.resilience.config import IdempotencyConfig
from lexigram.result import Result

if TYPE_CHECKING:
    from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol

logger = get_logger(__name__)

_IDEMPOTENCY_KEY_HEADER = "idempotency-key"


class IdempotencyMiddleware:
    """Framework-agnostic idempotency deduplication middleware.

    Reads the ``Idempotency-Key`` HTTP header from an incoming request.  When
    the key has been seen before (and the stored result has not expired), the
    original response is returned immediately without calling the downstream
    handler.  When the key is new the handler is invoked, and its response is
    stored against the key for future duplicate requests.

    Typical usage::

        store = InMemoryIdempotencyStore()
        middleware = IdempotencyMiddleware(store=store)

        # In a simplified ASGI handler or test:
        response = await middleware.process(
            headers={"idempotency-key": "req-abc-123"},
            handler=my_handler,
        )

    Args:
        store: Backend used to persist idempotency records.
        config: Idempotency configuration (TTL, key prefix, etc.).
        header_name: HTTP header name to inspect (default: ``idempotency-key``).
    """

    def __init__(
        self,
        store: IdempotencyStoreProtocol,
        config: IdempotencyConfig | None = None,
        header_name: str = _IDEMPOTENCY_KEY_HEADER,
    ) -> None:
        self._store = store
        self._config = config or IdempotencyConfig()
        self._header_name = header_name.lower()

    def _extract_key(self, headers: dict[str, str]) -> str | None:
        """Return the idempotency key from normalised lowercase headers.

        Args:
            headers: Request headers with lower-cased keys.

        Returns:
            The raw header value, or ``None`` when the header is absent.
        """
        raw = headers.get(self._header_name)
        if not raw:
            return None
        raw = raw.strip()
        if len(raw) > self._config.max_key_length:
            logger.warning(
                "Idempotency-Key header exceeds max length (%d); ignoring.",
                self._config.max_key_length,
            )
            return None
        return f"{self._config.key_prefix}{raw}"

    async def process(
        self,
        headers: dict[str, str],
        handler: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Run the handler with idempotency deduplication.

        When an ``Idempotency-Key`` header is present:

        * **Cache hit** — deserialise and return the stored response without
          invoking *handler*.
        * **Cache miss** — call *handler*, serialise the result, persist it,
          and return the result.

        When the header is absent the handler is called directly (pass-through).

        Args:
            headers: Lower-cased request headers.
            handler: Async callable that produces the response.  Called with
                ``(headers, *args, **kwargs)`` when no cache hit.
            *args: Forwarded to *handler* on cache miss.
            **kwargs: Forwarded to *handler* on cache miss.

        Returns:
            The response — either the freshly-computed one or the replayed
            stored result.
        """
        key = self._extract_key(headers)
        if key is None:
            # No Idempotency-Key header; pass through unchanged.
            return await handler(*args, **kwargs)

        try:
            cached_result = await self._store.get(key)
        except (OSError, ConnectionError, RuntimeError, IdempotencyStoreError):
            logger.warning(
                "Idempotency store unavailable on read for key %r; degrading to pass-through.",
                key,
            )
            return await handler(*args, **kwargs)

        if isinstance(cached_result, Result):
            if cached_result.is_err():
                logger.warning(
                    "Idempotency store unavailable on read for key %r; degrading to pass-through.",
                    key,
                )
                return await handler(*args, **kwargs)
            cached = cached_result.unwrap()
        else:
            cached = cached_result  # type: ignore[unreachable]  # type: ignore[unreachable]
        if cached is not None:
            logger.debug("Idempotency cache hit for key %r; replaying.", key)
            try:
                return serialization.loads(cached)
            except (serialization.JSONDecodeError, TypeError):
                # Stored value is already a Python object (in-memory store).
                return cached

        result = await handler(*args, **kwargs)

        try:
            serialised: Any = serialization.dumps(result)
        except (TypeError, ValueError):
            # Non-serialisable result (e.g., an object); store as-is.
            serialised = result

        try:
            await self._store.set(key, serialised, ttl=float(self._config.ttl))
            logger.debug(
                "Idempotency result cached for key %r (ttl=%ds).", key, self._config.ttl
            )
        except (OSError, ConnectionError, RuntimeError, IdempotencyStoreError):
            logger.warning(
                "Idempotency store unavailable on write for key %r; result not cached.",
                key,
            )
        return result


__all__ = ["IdempotencyMiddleware"]
