"""Governance policy engine — evaluates AI requests against declarative rules.

Policies are loaded from :class:`~store.PolicyStore` and evaluated in
priority order.  The first matching DENY rule short-circuits and returns
a :class:`~types.PolicyViolation`.  If no DENY is matched (or all rules
ALLOW), the request proceeds.
"""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING

from lexigram.ai.governance.policy.types import (
    GovernanceContext,
    PolicyDecision,
    PolicyEffect,
    PolicyScope,
    PolicyViolation,
)
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.ai.governance.policy.store import PolicyStore

logger = get_logger(__name__)


class PolicyEngine:
    """Evaluate AI usage against governance policies.

    Policies are declarative rules (stored in :class:`~store.PolicyStore`)
    that gate:

    * Which models can be used by which roles / services.
    * Maximum cost per request.
    * Required guardrails for specific model classes.
    * Data-classification rules (e.g. no PII to external models).

    Rule evaluation logic:

    1. Load all enabled policies from the store, sorted by priority.
    2. For each policy, check each rule against the request context.
    3. First rule whose condition matches and whose effect is ``DENY``
       → return ``Err(PolicyViolation)``.
    4. If no DENY is encountered → return ``Ok(PolicyDecision(allowed=True))``.

    Example::

        engine = PolicyEngine(store=PolicyStore())
        result = await engine.evaluate(
            request=context,
            context=GovernanceContext(model="gpt-4", ...),
        )
        if result.is_err():
            raise PermissionError(str(result.unwrap_err()))
    """

    def __init__(self, store: PolicyStore) -> None:
        """Initialize the engine with a policy store.

        Args:
            store: Store providing the policies to evaluate.
        """
        self._store = store

    async def evaluate(
        self,
        context: GovernanceContext,
    ) -> Result[PolicyDecision, PolicyViolation]:
        """Evaluate *context* against all active policies.

        Args:
            context: Governance context for the current AI request.

        Returns:
            ``Ok(PolicyDecision(allowed=True))`` when the request is
            permitted, ``Err(PolicyViolation)`` when a policy denies it.
        """
        policies = await self._store.get_policies(scope=context.role)

        for policy in policies:
            for rule in policy.rules:
                # Role filter — skip rules that don't apply to this role
                if rule.roles and context.role not in rule.roles:
                    continue

                if not self._matches_rule(rule.scope, rule.condition, context):
                    continue

                # Rule matches
                if rule.effect == PolicyEffect.DENY:
                    reason = self._denial_reason(rule.scope, rule.condition, context)
                    logger.warning(
                        "policy_engine_deny",
                        policy=policy.name,
                        scope=rule.scope,
                        model=context.model,
                        role=context.role,
                        reason=reason,
                    )
                    return Err(
                        PolicyViolation(
                            policy_name=policy.name,
                            reason=reason,
                            context=context,
                        )
                    )

        return Ok(PolicyDecision(allowed=True))

    # ------------------------------------------------------------------
    # Rule matching helpers
    # ------------------------------------------------------------------

    def _matches_rule(
        self,
        scope: PolicyScope,
        condition: dict,
        ctx: GovernanceContext,
    ) -> bool:
        """Return True when *condition* applies to *ctx* under *scope*."""
        if scope == PolicyScope.MODEL:
            pattern = condition.get("model_pattern", "*")
            return fnmatch.fnmatch(ctx.model, pattern)

        if scope == PolicyScope.COST:
            max_cost = condition.get("max_cost")
            if max_cost is None:
                return False
            return ctx.estimated_cost > max_cost

        if scope == PolicyScope.GUARDRAIL:
            # Match when a required guardrail is not listed in context metadata
            required: list[str] = condition.get("required", [])
            active_guards: list[str] = ctx.metadata.get("active_guardrails", [])
            return any(g not in active_guards for g in required)

        if scope == PolicyScope.DATA_CLASSIFICATION:
            classification = condition.get("classification", "public")
            return ctx.data_classification == classification

        return False

    def _denial_reason(
        self,
        scope: PolicyScope,
        condition: dict,
        ctx: GovernanceContext,
    ) -> str:
        """Build a human-readable denial reason string."""
        if scope == PolicyScope.MODEL:
            return (
                f"Model '{ctx.model}' matches denied pattern "
                f"'{condition.get('model_pattern', '*')}'"
            )
        if scope == PolicyScope.COST:
            return (
                f"Estimated cost {ctx.estimated_cost:.4f} USD exceeds "
                f"per-request limit {condition.get('max_cost', 0):.4f} USD"
            )
        if scope == PolicyScope.GUARDRAIL:
            missing = [
                g
                for g in condition.get("required", [])
                if g not in ctx.metadata.get("active_guardrails", [])
            ]
            return f"Required guardrails not active: {missing}"
        if scope == PolicyScope.DATA_CLASSIFICATION:
            return (
                f"Data classification '{ctx.data_classification}' is not "
                f"permitted for this request"
            )
        return f"Policy rule matched (scope={scope})"


__all__ = ["PolicyEngine"]
