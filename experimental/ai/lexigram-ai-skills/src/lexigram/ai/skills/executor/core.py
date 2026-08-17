"""SkillExecutor — executes skills with retry, caching, and permission checks."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, Protocol, cast

from lexigram.ai.skills.exceptions import (
    SkillNotFoundError,
    SkillPermissionDeniedError,
    SkillTimeoutError,
    SkillValidationError,
)
from lexigram.contracts.ai.skills import SkillError, SkillResult
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.ai.skills import SkillRegistryProtocol
    from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol


class PermissionCheckerProtocol(Protocol):
    """Protocol for permission checking on skill execution.

    Defines the interface for verifying user access to skill execution
    based on required permissions.
    """

    def check(self, user_id: str, permissions: set[str]) -> bool:
        """Check if user has required permissions.

        Args:
            user_id: The user identifier.
            permissions: Set of required permission strings.

        Returns:
            True if user has all required permissions, False otherwise.
        """
        ...


logger = get_logger(__name__)


class SkillExecutor:
    """Executes skills with the full production lifecycle.

    Handles skill resolution, permission checking, parameter validation,
    result caching, retry with exponential backoff, timeout enforcement,
    and observability logging.
    """

    def __init__(
        self,
        registry: SkillRegistryProtocol,
        *,
        cache: CacheBackendProtocol | None = None,
        permission_checker: PermissionCheckerProtocol | None = None,
        semaphore: asyncio.Semaphore | None = None,
    ) -> None:
        """Initialise the executor.

        Args:
            registry: SkillRegistryProtocol implementation.
            cache: Optional CacheBackendProtocol for caching deterministic results.
            permission_checker: Optional PermissionCheckerProtocol for access control.
            semaphore: Optional semaphore limiting concurrent executions.
        """
        self._registry = registry
        self._cache = cache
        self._permissions = permission_checker
        self._semaphore = semaphore

    async def execute(
        self,
        skill_name: str,
        params: dict[str, Any],
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> Result[SkillResult, SkillError]:
        """Execute a skill with full lifecycle management.

        Steps: resolve → check permissions → validate → check cache →
        execute with retry → store cache → return.

        Args:
            skill_name: Registered name of the skill to execute.
            params: Skill parameters.
            user_id: Optional caller identity for permission checks.
            session_id: Optional session context (passed through to metadata).

        Returns:
            Result wrapping SkillResult on success or SkillError on failure.
        """
        start = time.monotonic()

        # 1. Resolve skill
        skill = self._registry.get(skill_name)
        if skill is None:
            return Err(SkillNotFoundError(skill_name))

        defn = skill.definition

        # 2. Permission check
        if self._permissions and defn.permissions and user_id is not None:
            allowed = self._permissions.check(
                user_id,
                set(defn.permissions),
            )
            if not allowed:
                return Err(SkillPermissionDeniedError(skill_name, defn.permissions))

        # 3. Validate parameters
        errors = skill.validate(params)
        if errors:
            return Err(SkillValidationError(skill_name, errors))

        # 4. Cache lookup
        if defn.cacheable and self._cache is not None:
            cache_result = cast(
                "SkillResult | None",
                await self._cache.get(skill_name, params),  # type: ignore[call-arg]
            )
            if cache_result is not None:
                logger.debug("skill_cache_hit", skill=skill_name)
                return Ok(
                    SkillResult(
                        skill_name=skill_name,
                        success=True,
                        output=cache_result.output,
                        cached=True,
                        duration_ms=0.0,
                        metadata={"session_id": session_id},
                    )
                )

        # 5. Execute with retry
        last_error: SkillError | None = None
        for attempt in range(defn.max_retries + 1):
            try:
                coro = skill.execute(**params)
                if self._semaphore is not None:
                    async with self._semaphore:
                        result = await asyncio.wait_for(
                            coro, timeout=defn.timeout_seconds
                        )
                else:
                    result = await asyncio.wait_for(coro, timeout=defn.timeout_seconds)

                if result.is_ok():
                    sr = result.unwrap()
                    duration_ms = (time.monotonic() - start) * 1000
                    final = SkillResult(
                        skill_name=sr.skill_name,
                        success=sr.success,
                        output=sr.output,
                        error=sr.error,
                        duration_ms=duration_ms,
                        cached=sr.cached,
                        metadata={
                            **sr.metadata,
                            "session_id": session_id,
                            "attempt": attempt,
                        },
                    )
                    if defn.cacheable and self._cache is not None:
                        await self._cache.set(skill_name, params, final)  # type: ignore[arg-type]
                    logger.debug(
                        "skill_executed",
                        skill=skill_name,
                        attempt=attempt,
                        duration_ms=duration_ms,
                    )
                    return Ok(final)

                last_error = result.unwrap_err()

            except TimeoutError:
                last_error = SkillTimeoutError(skill_name, defn.timeout_seconds)
            except SkillError as exc:
                last_error = exc
            except Exception as exc:  # noqa: BLE001
                last_error = SkillError(
                    f"Unexpected error: {exc}", skill_name=skill_name
                )

            if attempt < defn.max_retries:
                backoff = min(2**attempt, 30)
                logger.debug(
                    "skill_retry",
                    skill=skill_name,
                    attempt=attempt,
                    backoff=backoff,
                    error=str(last_error),
                )
                await asyncio.sleep(backoff)

        duration_ms = (time.monotonic() - start) * 1000
        logger.warning(
            "skill_failed",
            skill=skill_name,
            duration_ms=duration_ms,
            error=str(last_error),
        )
        return Err(last_error or SkillError("Unknown error", skill_name=skill_name))


__all__ = ["SkillExecutor"]
