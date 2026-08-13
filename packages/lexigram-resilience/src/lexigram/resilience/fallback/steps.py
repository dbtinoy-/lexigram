from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Awaitable, Callable
import secrets
from typing import Any, TypeVar

from lexigram.contracts.infra.resilience.models import RetryConfig
from lexigram.logging import get_logger
from lexigram.resilience.exceptions import RetryExhaustedError
from lexigram.resilience.fallback.models import DegradationConfig
from lexigram.result import Err, Ok, Result

T = TypeVar("T")

logger = get_logger(__name__)


class FallbackStep(ABC):
    """Abstract base class for fallback steps."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    async def execute(
        self,
        context: dict[str, Any],
        error: Exception,
    ) -> Result[Any, Exception]:
        """Execute the fallback step."""
        ...


class RetryFallback(FallbackStep):
    """Retry fallback that attempts the operation multiple times."""

    def __init__(self, config: RetryConfig) -> None:
        super().__init__(f"retry_{id(self)}")
        self.config = config

    async def execute(
        self,
        context: Any,
        error: Exception,
    ) -> Result[Any, Exception]:
        """Execute retry logic."""
        attempt_key = f"_attempts_{self.name}"

        if hasattr(context, "get_metadata"):
            attempts = context.get_metadata(attempt_key, 0)
        elif isinstance(context, dict):
            attempts = context.get(attempt_key, 0)
        else:
            attempts = 0

        if self._should_retry(error):
            attempts += 1

            if hasattr(context, "add_metadata"):
                context.add_metadata(attempt_key, attempts)
            elif isinstance(context, dict):
                context[attempt_key] = attempts

            if attempts <= self.config.max_attempts:
                delay = self._calculate_delay(attempts)
                if self.config.on_retry:
                    self.config.on_retry(attempts, error)

                logger.info(
                    "Retrying operation (attempt %d/%d) after %.2fs",
                    attempts,
                    self.config.max_attempts,
                    delay,
                )
                await asyncio.sleep(delay)

                return Ok("__RETRY__")
            return Err(
                RetryExhaustedError(
                    f"Retry exhausted after {self.config.max_attempts} attempts",
                    last_error=error,
                ),
            )
        return Err(error)

    def _should_retry(self, error: Exception) -> bool:
        """Check if the error should trigger a retry."""
        return isinstance(error, self.config.retry_on)

    def _calculate_delay(self, attempts: int) -> float:
        """Calculate delay for next retry attempt."""
        delay = self.config.base_delay * (self.config.backoff_factor ** (attempts - 1))
        delay = min(delay, self.config.max_delay)

        if self.config.jitter:
            jitter_range = delay * 0.25
            delay += secrets.SystemRandom().uniform(-jitter_range, jitter_range)

        return max(0, delay)


class DegradationFallback(FallbackStep):
    """Fallback that returns a pre-configured degraded result."""

    def __init__(self, config: DegradationConfig) -> None:
        super().__init__(f"degradation_{id(self)}")
        self.config = config

    async def execute(
        self,
        context: Any,
        error: Exception,
    ) -> Result[Any, Exception]:
        """Return the degraded result."""
        if self.config.log_level:
            logger.log(
                self.config.log_level,
                "Operation degraded: %s",
                error,
            )
        else:
            logger.warning("Operation degraded: %s", error)

        return Ok(self.config.degraded_result)


class AlternativeFallback(FallbackStep):
    """Fallback that executes an alternative function."""

    def __init__(
        self,
        func: Callable[[Any, Exception], Awaitable[Result[Any, Exception]]],
    ) -> None:
        super().__init__(f"alternative_{id(self)}")
        self.func = func

    async def execute(
        self,
        context: Any,
        error: Exception,
    ) -> Result[Any, Exception]:
        """Execute the alternative function."""
        return await self.func(context, error)
