"""
Health monitoring for Lexigram Intelligence components.

This module provides health check capabilities for:
- LLM endpoints (connectivity, latency)
- Vector stores (connectivity, query performance)
- Cache services (connectivity, hit rates)
- Embedding services

Integrates with lexigram-monitor's health check system.
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts import (
    HealthCheckResult,
    HealthStatus,
)
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class AIHealthMonitor:
    """Health monitoring for intelligence components.

    Performs health checks on:
    - LLM endpoints
    - Vector stores
    - Cache services
    - Embedding services

    Example:
        >>> from lexigram.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> monitor = AIHealthMonitor()
        >>> # Add health checks
        >>> monitor.add_llm_check("openai", check_openai_health)
        >>> monitor.add_vector_check("pgvector", check_pgvector_health)
        >>> # Run all checks
        >>> results = await monitor.check_all()
        >>> if all(r.is_healthy() for r in results.values()):
        ...     logger.info("health_check", status="all_systems_healthy")
    """

    def __init__(self) -> None:
        """Initialize health monitor."""
        self._llm_checks: dict[str, Any] = {}
        self._vector_checks: dict[str, Any] = {}
        self._cache_checks: dict[str, Any] = {}
        self._embedding_checks: dict[str, Any] = {}

    def register_check(self, name: str, check: Any) -> None:
        """Register a named health-check callable.

        Args:
            name: Unique check name.
            check: An async callable returning a health status.
        """
        self._llm_checks[name] = check

    async def check(self) -> Any:
        """Run health checks and return a ``HealthCheckResult``-like object.

        Returns:
            An object with at least a ``status`` attribute.
        """
        return await self.check_all()

    def add_llm_check(self, provider: str, check_func: Any) -> None:
        """Add LLM health check.

        Args:
            provider: LLM provider name
            check_func: Async function that returns HealthCheckResult
        """
        self._llm_checks[provider] = check_func

    def add_vector_check(self, provider: str, check_func: Any) -> None:
        """Add vector store health check.

        Args:
            provider: Vector store provider name
            check_func: Async function that returns HealthCheckResult
        """
        self._vector_checks[provider] = check_func

    def add_cache_check(self, service: str, check_func: Any) -> None:
        """Add cache service health check.

        Args:
            service: Cache service name
            check_func: Async function that returns HealthCheckResult
        """
        self._cache_checks[service] = check_func

    def add_embedding_check(self, model: str, check_func: Any) -> None:
        """Add embedding service health check.

        Args:
            model: Embedding model name
            check_func: Async function that returns HealthCheckResult
        """
        self._embedding_checks[model] = check_func

    async def check_llm(self, provider: str) -> HealthCheckResult:
        """Check LLM endpoint health.

        Args:
            provider: LLM provider name

        Returns:
            Health check result
        """
        if provider not in self._llm_checks:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                component=f"llm.{provider}",
                message="No health check configured",
            )

        try:
            result = await self._llm_checks[provider]()
        except (
            Exception
        ) as e:  # health check must catch all failures and return UNHEALTHY
            logger.exception("Health check for %s failed", provider)
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component=f"llm.{provider}",
                message=f"Health check failed: {e!s}",
                error=str(e),
                details={"error": str(e)},
            )
        else:
            return result

    async def check_vector(self, provider: str) -> HealthCheckResult:
        """Check vector store health.

        Args:
            provider: Vector store provider name

        Returns:
            Health check result
        """
        if provider not in self._vector_checks:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                component=f"vector.{provider}",
                message="No health check configured",
            )

        try:
            result = await self._vector_checks[provider]()
        except (
            Exception
        ) as e:  # health check must catch all failures and return UNHEALTHY
            logger.exception("Health check for vector store %s failed", provider)
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component=f"vector.{provider}",
                message=f"Health check failed: {e!s}",
                error=str(e),
                details={"error": str(e)},
            )
        else:
            return result

    async def check_cache(self, service: str) -> HealthCheckResult:
        """Check cache service health.

        Args:
            service: Cache service name

        Returns:
            Health check result
        """
        if service not in self._cache_checks:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                component=f"cache.{service}",
                message="No health check configured",
            )

        try:
            result = await self._cache_checks[service]()
        except (
            Exception
        ) as e:  # health check must catch all failures and return UNHEALTHY
            logger.exception("Health check for cache service %s failed", service)
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component=f"cache.{service}",
                message=f"Health check failed: {e!s}",
                error=str(e),
                details={"error": str(e)},
            )
        else:
            return result

    async def check_all(self) -> dict[str, HealthCheckResult]:
        """Run all health checks.

        Returns:
            Dictionary mapping component names to health check results
        """
        results = {}

        # Check all LLM endpoints
        for provider in self._llm_checks:
            results[f"llm.{provider}"] = await self.check_llm(provider)

        # Check all vector stores
        for provider in self._vector_checks:
            results[f"vector.{provider}"] = await self.check_vector(provider)

        # Check all cache services
        for service in self._cache_checks:
            results[f"cache.{service}"] = await self.check_cache(service)

        # Check all embedding services
        for model in self._embedding_checks:
            if model in self._embedding_checks:
                try:
                    results[f"embedding.{model}"] = await self._embedding_checks[
                        model
                    ]()
                except (
                    Exception
                ) as e:  # health check must catch all failures and return UNHEALTHY
                    logger.exception(
                        "Health check for embedding model %s failed",
                        model,
                    )
                    results[f"embedding.{model}"] = HealthCheckResult(
                        status=HealthStatus.UNHEALTHY,
                        component=f"embedding.{model}",
                        message=f"Health check failed: {e!s}",
                        error=str(e),
                        details={"error": str(e)},
                    )

        return results

    async def is_ready(self) -> bool:
        """Check if all components are ready (healthy or degraded).

        Returns:
            True if all components are ready, False otherwise
        """
        results = await self.check_all()
        return all(
            r.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
            for r in results.values()
        )

    async def is_live(self) -> bool:
        """Check if service is alive (at least one component healthy).

        Returns:
            True if at least one component is healthy, False otherwise
        """
        results = await self.check_all()
        if not results:
            return True  # No checks configured = assume live

        return any(r.status == HealthStatus.HEALTHY for r in results.values())
