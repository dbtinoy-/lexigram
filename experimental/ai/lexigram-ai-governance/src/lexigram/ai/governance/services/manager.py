"""AI usage governance — budget limits, rate limits, model restrictions."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from lexigram.ai.governance.exceptions import GovernancePersistenceError
from lexigram.ai.governance.services.governance_audit import (
    emit_audit_event,
    notify_soft_limit,
)
from lexigram.ai.governance.services.model_policy import model_access_allowed
from lexigram.ai.governance.services.resource_coordinator import (
    ResourceUnitCoordinator,
)
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.ai.governance.audit import AIAuditStore
    from lexigram.ai.governance.config import GovernanceConfig
    from lexigram.ai.governance.exceptions import GovernanceError
    from lexigram.ai.governance.persistence import GovernancePersistence
    from lexigram.ai.governance.resource.tracker import ResourceUnitTracker
    from lexigram.contracts.infra.cache import CacheBackendProtocol

logger = get_logger(__name__)

_PERSISTENCE_FAILURE_EXCEPTIONS: tuple[type[Exception], ...] = (
    GovernancePersistenceError,
    OSError,
    ConnectionError,
    RuntimeError,
    ValueError,
    TypeError,
)


@inject
class AIGovernanceManager:
    """Enforces AI usage policies: budget limits, rate limits, model restrictions.

    Implements ``AIGovernanceProtocol`` from contracts.

    Governance state (request counts, spend totals) is delegated to a
    :class:`~lexigram.ai.governance.persistence.GovernancePersistence`
    backend so the storage strategy is swappable without changing policy
    logic.  With no explicit *persistence*, a Redis backend is built when
    *cache* is given, else an in-memory backend.  Audit emission lives in
    :mod:`.governance_audit`; resource-unit consumption in
    :mod:`.resource_coordinator`.

    Args:
        config: Governance policy configuration.
        cache: Optional cache backend used to auto-create a Redis persistence
            backend.  Ignored when *persistence* is supplied explicitly.
        persistence: Explicit persistence backend.  Takes precedence over *cache*.
        on_soft_limit: Optional async callback invoked when the monthly spend
            crosses the ``soft_limit_pct`` threshold.  Signature:
            ``async def cb(user_id, current_spend, budget) -> None``.
        audit_store: Optional audit store for recording governance decisions.
            When provided, every governance check (allowed or denied) and
            every cost-tracking call is recorded as an audit event.
    """

    def __init__(
        self,
        config: GovernanceConfig,
        cache: CacheBackendProtocol | None = None,
        persistence: GovernancePersistence | None = None,
        on_soft_limit: Callable[..., object] | None = None,
        audit_store: AIAuditStore | None = None,
    ) -> None:
        self._config = config
        self._on_soft_limit = on_soft_limit
        self._audit_store = audit_store
        self._background_tasks: set[asyncio.Task[object]] = set()

        if persistence is None:
            from lexigram.ai.governance.persistence import (
                InMemoryGovernancePersistence,
                RedisGovernancePersistence,
            )

            persistence = (
                RedisGovernancePersistence(cache)
                if cache is not None
                else InMemoryGovernancePersistence()
            )
        self._persistence = cast("GovernancePersistence", persistence)

        self._resources = ResourceUnitCoordinator(config, self._persistence)

    @property
    def resource_tracker(self) -> ResourceUnitTracker | None:
        """The tracker instance, or ``None`` when no units are configured.

        Exposed for DI registration so the same tracker is shared across
        the application (consume/release calls go through here regardless
        of which service is resolved from the container).
        """
        return self._resources.tracker

    async def check_request(
        self,
        model: str,
        provider: str,
        user_id: str | None = None,
    ) -> bool:
        """Check if a request is allowed under governance policy.

        Args:
            model: Model identifier.
            provider: Provider name.
            user_id: Optional user identifier for per-user limits.

        Returns:
            True if request is allowed, False if blocked by policy.
        """
        if self._config.restricted_models and model in self._config.restricted_models:
            logger.warning(
                "governance_model_restricted", model=model, provider=provider
            )
            self._emit_audit(
                "model_denied",
                model=model,
                provider=provider,
                user_id=user_id,
                status="denied",
                metadata={"reason": "restricted_model"},
            )
            return False

        if not self.check_model_access(user_id, model):
            self._emit_audit(
                "model_denied",
                model=model,
                provider=provider,
                user_id=user_id,
                status="denied",
                metadata={"reason": "access_policy"},
            )
            return False

        if self._config.rpm_limit:
            try:
                count = await self._persistence.incr_requests(
                    user_id or "global", window=60.0
                )
            except _PERSISTENCE_FAILURE_EXCEPTIONS as exc:
                return self._on_persistence_failure(
                    "rpm_check", user_id or "global", exc
                )
            if count > self._config.rpm_limit:
                logger.warning(
                    "governance_rpm_exceeded",
                    user_id=user_id,
                    rpm_limit=self._config.rpm_limit,
                )
                self._emit_audit(
                    "rate_limited",
                    model=model,
                    provider=provider,
                    user_id=user_id,
                    status="denied",
                    metadata={
                        "rpm_limit": self._config.rpm_limit,
                        "current_rpm": count,
                    },
                )
                return False

        return True

    def check_model_access(self, user_id: str | None, model: str) -> bool:
        """Check if user is allowed to use the given model.

        Evaluates per-user ``model_allowlist`` / ``model_denylist`` glob
        patterns (e.g. ``"gpt-4*"``); see :mod:`.model_policy`.

        Args:
            user_id: User identifier, or ``None`` for anonymous / global.
            model: Model name to check.

        Returns:
            True if access is permitted, False if denied.
        """
        return model_access_allowed(self._config, user_id, model)

    async def check_budget(self, cost: float, user_id: str | None = None) -> bool:
        """Check if a cost would exceed the monthly budget.

        Warns (and invokes ``on_soft_limit``) when the spend crosses the
        configured soft-limit threshold; blocks only past the hard budget.

        Args:
            cost: Estimated cost of the request.
            user_id: Optional user identifier.

        Returns:
            True if within hard budget, False if would exceed.
        """
        if not self._config.enforce_budget:
            return True
        if self._config.monthly_budget is None:
            return True

        try:
            current = await self._get_monthly_spend(user_id)
        except _PERSISTENCE_FAILURE_EXCEPTIONS as exc:
            return self._on_persistence_failure(
                "budget_check", f"{user_id or 'global'}:{_current_month()}", exc
            )
        budget = self._config.monthly_budget

        # Soft-limit warning (does not block)
        if (
            self._config.soft_limit_pct is not None
            and current + cost >= budget * self._config.soft_limit_pct
            and current < budget * self._config.soft_limit_pct
        ):
            logger.warning(
                "governance_soft_limit_reached",
                user_id=user_id,
                current_spend=current,
                soft_limit_pct=self._config.soft_limit_pct,
                monthly_budget=budget,
            )
            self._emit_audit(
                "soft_limit_reached",
                user_id=user_id,
                cost=cost,
                metadata={
                    "current_spend": current,
                    "soft_limit_pct": self._config.soft_limit_pct,
                    "monthly_budget": budget,
                },
            )
            notify_soft_limit(
                self._on_soft_limit, self._background_tasks, user_id, current, budget
            )

        allowed = current + cost <= budget
        if not allowed:
            logger.warning(
                "governance_budget_exceeded",
                user_id=user_id,
                current_spend=current,
                request_cost=cost,
                monthly_budget=budget,
            )
            self._emit_audit(
                "budget_exceeded",
                user_id=user_id,
                cost=cost,
                status="denied",
                metadata={
                    "current_spend": current,
                    "request_cost": cost,
                    "monthly_budget": budget,
                },
            )
        return allowed

    async def check_request_budget(
        self,
        estimated_cost: float,
        request_id: str | None = None,
    ) -> Result[None, GovernanceError]:
        """Check if a single request cost is within the per-request budget.

        Validates *estimated_cost* against ``max_request_cost`` (per-request
        cap) first, then against the monthly budget via :meth:`check_budget`.

        Args:
            estimated_cost: Estimated cost in USD for this request.
            request_id: Optional request identifier for logging context.

        Returns:
            ``Ok(None)`` if within all budget limits, else
            ``Err(GovernanceError)``.
        """
        from lexigram.ai.governance.exceptions import GovernanceError

        if not self._config.enforce_budget:
            return Ok(None)

        if (
            self._config.max_request_cost is not None
            and estimated_cost > self._config.max_request_cost
        ):
            logger.warning(
                "governance_request_cost_exceeded",
                estimated_cost=estimated_cost,
                max_request_cost=self._config.max_request_cost,
                request_id=request_id,
            )
            self._emit_audit(
                "request_budget_exceeded",
                cost=estimated_cost,
                status="denied",
                metadata={
                    "estimated_cost": estimated_cost,
                    "max_request_cost": self._config.max_request_cost,
                    "request_id": request_id,
                },
            )
            return Err(
                GovernanceError(
                    f"Request cost ${estimated_cost:.4f} exceeds per-request "
                    f"limit ${self._config.max_request_cost:.4f}"
                )
            )

        allowed = await self.check_budget(estimated_cost)
        if not allowed:
            return Err(
                GovernanceError(
                    f"Request cost ${estimated_cost:.4f} would exceed monthly budget"
                )
            )

        return Ok(None)

    async def track_cost(
        self,
        cost: float,
        model: str,
        user_id: str | None = None,
    ) -> None:
        """Record AI usage cost.

        Args:
            cost: Cost to record.
            model: Model that generated the cost.
            user_id: Optional user identifier.
        """
        key = user_id or "global"
        month_key = f"{key}:{_current_month()}"
        try:
            await self._persistence.add_spend(month_key, cost, ttl=32 * 24 * 3600)
        except _PERSISTENCE_FAILURE_EXCEPTIONS as exc:
            self._on_persistence_failure("cost_track", month_key, exc)
            return
        logger.debug("governance_cost_tracked", cost=cost, model=model, user_id=user_id)

    def reload_config(self, config: GovernanceConfig) -> None:
        """Hot-reload governance configuration without restart.

        Atomically swaps the config reference so subsequent checks use the
        new limits.  Persistence state is untouched.

        Args:
            config: New governance configuration to apply.
        """
        self._config = config
        logger.info(
            "governance_config_reloaded",
            monthly_budget=config.monthly_budget,
            rpm_limit=config.rpm_limit,
            soft_limit_pct=config.soft_limit_pct,
            restricted_models=config.restricted_models,
        )
        self._emit_audit(
            "config_reloaded",
            metadata={
                "monthly_budget": config.monthly_budget,
                "rpm_limit": config.rpm_limit,
                "soft_limit_pct": config.soft_limit_pct,
            },
        )

    # Cross-cutting helpers (audit + fail-open/closed decision)
    def _emit_audit(
        self,
        event_type: str,
        *,
        model: str | None = None,
        provider: str | None = None,
        user_id: str | None = None,
        status: str = "success",
        tokens: int | None = None,
        cost: float | None = None,
        latency_ms: float | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Fire-and-forget audit event recording (see :mod:`.governance_audit`)."""
        emit_audit_event(
            self._audit_store,
            self._background_tasks,
            event_type,
            model=model,
            provider=provider,
            user_id=user_id,
            status=status,
            tokens=tokens,
            cost=cost,
            latency_ms=latency_ms,
            metadata=metadata,
        )

    def _on_persistence_failure(
        self,
        operation: str,
        bucket_key: str,
        exception: BaseException,
    ) -> bool:
        """Apply the configured decision when the persistence backend fails.

        Logs the failure and returns whether the caller should allow the
        request (fail-open) or deny it (fail-closed default).  Failures are
        never re-raised: agent-executor callers treat a raised governance
        exception as allow-through, so raising would defeat fail-closed.

        Args:
            operation: Failing governance operation (``"rpm_check"``, ...).
            bucket_key: Bucket key the operation was reading or writing.
            exception: The exception raised by the persistence backend.

        Returns:
            True to allow (fail-open configured), False to deny.
        """
        fail_open = self._config.fail_open_on_persistence_error
        logger.warning(
            "governance_persistence_unavailable",
            operation=operation,
            bucket_key=bucket_key,
            error_type=type(exception).__name__,
            decision="allowed" if fail_open else "denied",
            fail_open=fail_open,
        )
        return fail_open

    async def _get_monthly_spend(self, user_id: str | None) -> float:
        key = user_id or "global"
        month_key = f"{key}:{_current_month()}"
        return await self._persistence.get_spend(month_key)

    # -- Resource unit delegation --------------------------------------------

    async def consume_resource(
        self,
        tenant_id: str,
        unit_name: str,
        amount: float,
        actor_id: str | None = None,
    ) -> Result:
        """Consume *amount* of a resource unit for *tenant_id*.

        Delegates to the resource coordinator's tracker if configured.
        """
        return await self._resources.consume(tenant_id, unit_name, amount, actor_id)

    async def release_resource(
        self,
        tenant_id: str,
        unit_name: str,
        amount: float,
    ) -> None:
        """Release *amount* of a held resource (INSTANTANEOUS units only)."""
        await self._resources.release(tenant_id, unit_name, amount)

    async def resource_usage(self, tenant_id: str, unit_name: str):
        """Return current usage snapshot for *tenant_id* + *unit_name*."""
        return await self._resources.usage(tenant_id, unit_name)


def _current_month() -> str:
    """Return current year-month string for cache key scoping."""
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m")


__all__ = ["AIGovernanceManager"]
