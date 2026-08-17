"""DI-injectable content policy service.

:class:`ContentPolicyService` wraps a :class:`~gates.CompositeGate` (or
any single :class:`~protocol.ContentPolicyGateProtocol`) and adds
structured observability: every ``evaluate()`` call emits a structured log
event with ``principal_id``, ``content_type``, ``outcome``, and ``reason``.

Applications inject this service into their AI pipelines and call
``evaluate()`` **before** invoking the LLM.  See the README for the
canonical call shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.governance.content_gate.models import PolicyDecision, PolicyOutcome
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.ai.governance.content_gate.models import PolicyRequest
    from lexigram.ai.governance.content_gate.protocol import (
        ContentPolicyGateProtocol,
        PolicyObserverProtocol,
    )

logger = get_logger(__name__)


class ContentPolicyService:
    """Evaluates content policy before an LLM request is dispatched.

    This service is the primary DI-injectable surface for content gating.
    It wraps a single gate (which may itself be a :class:`~gates.CompositeGate`)
    and adds structured logging for every decision so that operators have
    an audit trail without coupling gate implementations to a specific logger.

    Args:
        gate: The gate (or composite) to delegate to.
        observers: Additional observers notified after each evaluation.
            These are layered on top of any observers already configured in
            the gate itself.
    """

    def __init__(
        self,
        gate: ContentPolicyGateProtocol,
        observers: list[PolicyObserverProtocol] | None = None,
    ) -> None:
        self._gate = gate
        self._observers: list[PolicyObserverProtocol] = list(observers or [])

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        """Evaluate *request* and emit a structured log event.

        Apps call this method before dispatching to an LLM.  If the returned
        ``outcome`` is ``DENY``, the caller must not proceed::

            decision = await policy_service.evaluate(request)
            if decision.outcome == PolicyOutcome.DENY:
                raise ContentPolicyViolation(decision.reason)

        Args:
            request: Context about the content and the requesting principal.

        Returns:
            A :class:`~models.PolicyDecision`.  Never raises for domain-level
            outcomes; infrastructure errors propagate normally.
        """
        decision = await self._gate.evaluate(request)

        logger.info(
            "content_policy_evaluated",
            principal_id=request.principal_id,
            content_type=request.content_type,
            outcome=decision.outcome,
            reason=decision.reason,
        )

        for observer in self._observers:
            await observer.on_decision(request, decision)

        return decision

    def is_allowed(self, decision: PolicyDecision) -> bool:
        """Convenience predicate — ``True`` for ALLOW or THROTTLE outcomes.

        Args:
            decision: A decision previously returned by :meth:`evaluate`.

        Returns:
            ``False`` only when *outcome* is ``DENY``.
        """
        return decision.outcome != PolicyOutcome.DENY


__all__ = ["ContentPolicyService"]
