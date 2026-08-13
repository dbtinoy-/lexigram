"""Content policy gate protocols.

Defines the ``ContentPolicyGateProtocol`` that application gates must
implement, and the ``PolicyObserverProtocol`` for pluggable side-effects
(metrics, external audit systems, etc.).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lexigram.ai.governance.content_gate.models import PolicyDecision, PolicyRequest


@runtime_checkable
class ContentPolicyGateProtocol(Protocol):
    """Gate that decides whether a request should reach the LLM.

    Implementations are responsible for a single evaluation concern
    (e.g. abuse detection, quota enforcement, age gating, jurisdictional
    restrictions).  Complex policies are composed via :class:`~gates.CompositeGate`.

    The method must be **async** and must never raise for domain-level
    outcomes — ``DENY`` is returned as a :class:`~models.PolicyDecision`,
    not raised as an exception.  Infrastructure failures (DB down, etc.)
    *may* raise.
    """

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        """Evaluate *request* and return a policy decision.

        Args:
            request: Contextual information about the content and caller.

        Returns:
            A :class:`~models.PolicyDecision` with one of
            ``ALLOW``, ``DENY``, or ``THROTTLE``.
        """
        ...


@runtime_checkable
class PolicyObserverProtocol(Protocol):
    """Side-effect hook called after every gate evaluation.

    Observers receive the original request and the final decision.  They must
    not mutate the decision.  Use for metrics, external audit streams, or
    custom structured logging.

    Observers are invoked asynchronously by :class:`~gates.CompositeGate`
    and :class:`~service.ContentPolicyService`.  Infrastructure errors inside
    an observer must be handled by the observer implementation.
    """

    async def on_decision(
        self,
        request: PolicyRequest,
        decision: PolicyDecision,
    ) -> None:
        """Called after a gate produces a decision.

        Args:
            request: The original policy request.
            decision: The decision that was produced.
        """
        ...


__all__ = [
    "ContentPolicyGateProtocol",
    "PolicyObserverProtocol",
]
