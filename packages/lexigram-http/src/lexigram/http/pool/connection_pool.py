"""Connection pool implementation.

Wraps ``aiohttp``'s connection pooling with configurable limits and
timeout settings for efficient connection reuse.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import aiohttp

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.web.http_protocols import HTTPSessionProtocol

logger = get_logger(__name__)


class ConnectionPool:
    """Async HTTP connection pool backed by ``aiohttp``.

    Args:
        max_connections: Maximum total concurrent connections (default: 10).
        max_keepalive_connections: Keep-alive connections per host (default: 5).
        timeout: Request timeout in seconds (default: 30.0).
        ttl_dns_cache: DNS cache TTL in seconds (default: 300).
        force_close: Force-close connections after each use (default: False).
        verify_ssl: Verify SSL certificates (default: True). Set to ``False``
            only in trusted internal networks — never in production for
            external endpoints.

    Example::

        pool = ConnectionPool(max_connections=100, timeout=60.0)
        await pool.start()
        response = await pool._session.get("https://api.example.com")
        await pool.stop()
    """

    def __init__(
        self,
        max_connections: int = 10,
        max_keepalive_connections: int = 5,
        max_connections_per_host: int = 10,
        timeout: float = 30.0,
        ttl_dns_cache: int = 300,
        force_close: bool = False,
        verify_ssl: bool = True,
        proxy: str | None = None,
        trust_env: bool = True,
        cookie_jar: bool = True,
    ) -> None:
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.max_connections_per_host = max_connections_per_host
        self.timeout = timeout
        self.ttl_dns_cache = ttl_dns_cache
        self.force_close = force_close
        self.verify_ssl = verify_ssl
        self.proxy = proxy
        self.trust_env = trust_env
        self.cookie_jar = cookie_jar
        self._session: HTTPSessionProtocol | None = None

    async def start(self) -> None:
        """Initialise the connection pool and create the ``aiohttp`` session."""
        if self._session is None:
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=self.max_connections_per_host,
                ttl_dns_cache=self.ttl_dns_cache,
                force_close=self.force_close,
                ssl=None if self.verify_ssl else False,  # type: ignore[arg-type]
            )
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            jar = aiohttp.CookieJar() if self.cookie_jar else aiohttp.DummyCookieJar()
            self._session = cast(
                "HTTPSessionProtocol",
                aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    cookie_jar=jar,
                    trust_env=self.trust_env,
                ),
            )

    async def stop(self) -> None:
        """Close the connection pool and release all resources."""
        if self._session:
            await self._session.close()
            self._session = None

    def is_started(self) -> bool:
        """Return ``True`` if the pool session is active."""
        return self._session is not None

    async def warm_up(self, urls: list[str]) -> None:
        """Pre-establish connections to known endpoints.

        Fires a lightweight ``HEAD`` (falling back to ``GET``) request to each
        URL so that the TCP and TLS handshake has already been completed before
        the first real request arrives.  Errors are swallowed silently — this is
        a best-effort optimisation, not a connectivity check.

        Args:
            urls: Base URLs to pre-connect to (e.g. ``["https://api.example.com"]``).

        Example::

            await pool.start()
            await pool.warm_up(["https://api.example.com", "https://cdn.example.com"])
        """
        if not self._session:
            return
        import asyncio

        async def _ping(url: str) -> None:
            try:
                async with self._session.head(url, allow_redirects=False) as _:  # type: ignore[union-attr]
                    pass
                logger.debug("connection_pool.warm_up.success", url=url)
            except (OSError, ConnectionError, RuntimeError) as exc:
                logger.warning(
                    "connection_pool.warm_up.failed", url=url, error=str(exc)
                )

        await asyncio.gather(*(_ping(u) for u in urls), return_exceptions=True)


__all__ = ["ConnectionPool"]
