"""AI usage governance — budget limits, rate limits, model restrictions."""

from __future__ import annotations

import asyncio
import fnmatch
from typing import TYPE_CHECKING, cast

from lexigram.di.decorators import inject
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.ai.governance.audit import AIAuditStore
    from lexigram.ai.governance.config import GovernanceConfig
    from lexigram.ai.governance.exceptions import GovernanceError
    from lexigram.ai.governance.persistence import GovernancePersistence
    from lexigram.ai.governance.resource.registry import (  # noqa: F401
        ResourceUnitRegistry,
    )
    from lexigram.ai.governance.resource.tracker import (  # noqa: F401
        ResourceUnitTracker,
    )
    from lexigram.contracts.infra.cache import CacheBackendProtocol

logger = get_logger(__name__)


@inject
class AIGovernanceManager:
    """Enforces AI usage policies: budget limits, rate limits, model restrictions.

    Implements ``AIGovernanceProtocol`` from contracts.

    Governance state (request counts, spend totals) is delegated to a
    :class:`~lexigram.ai.governance.persistence.GovernancePersistence`
    backend so the storage strategy is swappable without changing policy
    logic.  When no explicit *persistence* is given, an
    :class:`~lexigram.ai.governance.persistence.InMemoryGovernancePersistence`
    instance is created automatically using the optional *cache* argument to
    build a :class:`~lexigram.ai.governance.persistence.RedisGovernancePersistence`
    when a cache backend is available.

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
        self._resource_registry: ResourceUnitRegistry | None = None
        self._resource_tracker: ResourceUnitTracker | None = None

        if persistence is not None:
            self._persistence = persistence
        elif cache is not None:
            from lexigram.ai.governance.persistence import (
                RedisGovernancePersistence,
            )

            self._persistence = cast(
                "GovernancePersistence", RedisGovernancePersistence(cache)
            )
        else:
            from lexigram.ai.governance.persistence import (
                InMemoryGovernancePersistence,
            )

            self._persistence = cast(
                "GovernancePersistence", InMemoryGovernancePersistence()
            )

        # Initialise resource unit tracker
        if config.resource_units:
            from lexigram.ai.governance.resource.registry import (
                ResourceUnitRegistry,
            )
            from lexigram.ai.governance.resource.tracker import (
                ResourceUnitTracker,
            )

            self._resource_registry = ResourceUnitRegistry.from_list(
                config.resource_units
            )
            self._resource_tracker = ResourceUnitTracker(
                registry=self._resource_registry,
                persistence=self._persistence,
            )
        else:
            self._resource_registry = None
            self._resource_tracker = None

    @property
    def resource_tracker(self) -> ResourceUnitTracker | None:
        """The :class:`ResourceUnitTracker` instance, or ``None`` when no
        resource units are configured.

        Exposed for DI registration so the same tracker is shared across the
        application (consume/release calls go through here regardless of
        whether the caller resolves ``AIGovernanceManager`` or
        ``ResourceUnitTracker`` from the container).
        """
        return self._resource_tracker

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
            count = await self._persistence.incr_requests(
                user_id or "global", window=60.0
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

        Evaluates per-user ``model_allowlist`` and ``model_denylist`` from
        :class:`~lexigram.ai.config.GovernanceConfig`.  Both support glob
        patterns (e.g. ``"gpt-4*"``, ``"claude-3-*"``).

        Logic:
        1. If ``model_allowlist`` has an entry for *user_id*, the model must
           match at least one pattern in the allowlist.
        2. If ``model_denylist`` has an entry for *user_id*, the model must
           not match any pattern in the denylist.
        3. When no entry exists for *user_id*, access is allowed.

        Args:
            user_id: User identifier, or ``None`` for anonymous / global.
            model: Model name to check.

        Returns:
            True if access is permitted, False if denied.
        """
        key = user_id or "global"

        allowlist = self._config.model_allowlist.get(
            key
        ) or self._config.model_allowlist.get("*")
        if allowlist:
            if not any(fnmatch.fnmatch(model, pattern) for pattern in allowlist):
                logger.warning(
                    "governance_model_not_in_allowlist",
                    user_id=user_id,
                    model=model,
                )
                return False

        denylist = self._config.model_denylist.get(
            key
        ) or self._config.model_denylist.get("*")
        if denylist:
            if any(fnmatch.fnmatch(model, pattern) for pattern in denylist):
                logger.warning(
                    "governance_model_in_denylist",
                    user_id=user_id,
                    model=model,
                )
                return False

        return True

    async def check_budget(self, cost: float, user_id: str | None = None) -> bool:
        """Check if a cost would exceed the monthly budget.

        Emits a structured warning when the spend crosses the configured
        ``soft_limit_pct`` threshold and invokes the optional
        ``on_soft_limit`` callback.  Returns ``False`` only when the hard
        limit (``monthly_budget``) would be exceeded.

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

        current = await self._get_monthly_spend(user_id)
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
            if self._on_soft_limit is not None:
                import asyncio
                import inspect

                result = self._on_soft_limit(user_id, current, budget)
                if inspect.isawaitable(result):
                    task = asyncio.ensure_future(result)
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)

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
            ``Ok(None)`` if within all budget limits.
            ``Err(GovernanceError)`` if either per-request or monthly limit
            is exceeded.
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
        await self._persistence.add_spend(month_key, cost, ttl=32 * 24 * 3600)
        logger.debug("governance_cost_tracked", cost=cost, model=model, user_id=user_id)

    def reload_config(self, config: GovernanceConfig) -> None:
        """Hot-reload governance configuration without restart.

        Atomically swaps the internal config reference so that subsequent policy
        checks use the new limits.  Does **not** touch persistence state — only
        the thresholds and rules are updated.

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

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------

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
        """Fire-and-forget audit event recording.

        Creates an :class:`~lexigram.ai.governance.audit.AIAuditEvent` and
        schedules ``record()`` on the audit store without blocking the
        caller.  Silently drops the event when no audit store is configured.
        """
        if self._audit_store is None:
            return

        from lexigram.ai.governance.audit import AIAuditEvent, AuditEventType

        event = AIAuditEvent(
            event_type=AuditEventType(event_type),
            model=model,
            provider=provider,
            user_id=user_id,
            status=status,
            tokens=tokens,
            cost=cost,
            latency_ms=latency_ms,
            metadata=dict(metadata) if metadata else {},
        )

        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        task = loop.create_task(self._audit_store.record(event))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

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

        Delegates to :class:`ResourceUnitTracker` if configured.
        """
        if self._resource_tracker is None:
            return Err(self._no_tracker_error(tenant_id, unit_name, amount))
        return await self._resource_tracker.consume(
            tenant_id, unit_name, amount, actor_id
        )

    async def release_resource(
        self,
        tenant_id: str,
        unit_name: str,
        amount: float,
    ) -> None:
        """Release *amount* of a held resource (INSTANTANEOUS units only)."""
        if self._resource_tracker is None:
            return
        await self._resource_tracker.release(tenant_id, unit_name, amount)

    async def resource_usage(
        self,
        tenant_id: str,
        unit_name: str,
    ):
        """Return current usage snapshot for *tenant_id* + *unit_name*."""
        if self._resource_tracker is None:
            from lexigram.contracts.ai.governance.resource_unit import (
                ResourceUsageSnapshot,
            )

            return ResourceUsageSnapshot(
                tenant_id=tenant_id,
                unit_name=unit_name,
                current=0.0,
                limit=0.0,
            )
        return await self._resource_tracker.usage(tenant_id, unit_name)

    def _no_tracker_error(self, tenant_id, unit_name, amount):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceExhaustedError,
        )

        return ResourceExhaustedError(
            tenant_id=tenant_id,
            unit_name=unit_name,
            limit=0,
            current=0,
        )


def _current_month() -> str:
    """Return current year-month string for cache key scoping."""
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m")


__all__ = ["AIGovernanceManager"]
