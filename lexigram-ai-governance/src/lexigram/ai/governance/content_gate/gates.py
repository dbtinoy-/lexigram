"""Built-in content policy gate implementations.

* :class:`AlwaysAllowGate` — trivial pass-through.  Useful as a default
  or in development when no real policy is needed.
* :class:`CompositeGate` — combines multiple gates with configurable logic.
  The default strategy: any ``DENY`` wins; otherwise the most-restrictive
  outcome (``THROTTLE`` beats ``ALLOW``) is returned and all reasons are
  aggregated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.governance.content_gate.models import PolicyDecision, PolicyOutcome
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lexigram.ai.governance.content_gate.models import PolicyRequest
    from lexigram.ai.governance.content_gate.protocol import (
        ContentPolicyGateProtocol,
        PolicyObserverProtocol,
    )

logger = get_logger(__name__)

# Outcome severity ordering — higher index = more restrictive.
_OUTCOME_ORDER: list[PolicyOutcome] = [
    PolicyOutcome.ALLOW,
    PolicyOutcome.THROTTLE,
    PolicyOutcome.DENY,
]


class AlwaysAllowGate:
    """Trivial gate that allows every request.

    Use as a default/no-op gate in development, testing, or when the
    application does not yet have a content policy.
    """

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        """Always return ALLOW.

        Args:
            request: Policy request (ignored).

        Returns:
            ``PolicyDecision(outcome=ALLOW, reason="")``.
        """
        logger.debug(
            "content_gate_always_allow",
            principal_id=request.principal_id,
            content_type=request.content_type,
        )
        return PolicyDecision(outcome=PolicyOutcome.ALLOW, reason="")


class CompositeGate:
    """Combines multiple :class:`~protocol.ContentPolicyGateProtocol` gates.

    **Evaluation algorithm:**

    1. All member gates are evaluated (no short-circuit on DENY so that all
       observers receive the full picture).
    2. If **any** gate returns ``DENY`` → the composite returns ``DENY``.
    3. Otherwise the most-restrictive outcome across all gates wins
       (``THROTTLE`` beats ``ALLOW``).
    4. All non-empty reason strings from member gates are aggregated,
       separated by ``"; "``.
    5. After the final decision is produced, each registered
       :class:`~protocol.PolicyObserverProtocol` is notified.

    Args:
        gates: One or more gate instances to compose.
        observers: Optional observers notified after each composite evaluation.
    """

    def __init__(
        self,
        gates: Sequence[ContentPolicyGateProtocol],
        observers: Sequence[PolicyObserverProtocol] | None = None,
    ) -> None:
        self._gates = list(gates)
        self._observers: list[PolicyObserverProtocol] = list(observers or [])

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        """Evaluate *request* against all member gates and return a composite decision.

        Args:
            request: Contextual information about the content and caller.

        Returns:
            The most-restrictive :class:`~models.PolicyDecision` across all
            member gates, with aggregated reasons.
        """
        decisions: list[PolicyDecision] = []
        for gate in self._gates:
            decision = await gate.evaluate(request)
            decisions.append(decision)

        final = self._merge(decisions)

        logger.info(
            "content_gate_composite_evaluated",
            principal_id=request.principal_id,
            content_type=request.content_type,
            outcome=final.outcome,
            reason=final.reason,
            gate_count=len(self._gates),
        )

        for observer in self._observers:
            await observer.on_decision(request, final)

        return final

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _merge(decisions: list[PolicyDecision]) -> PolicyDecision:
        """Merge a list of decisions into a single most-restrictive decision."""
        if not decisions:
            return PolicyDecision(outcome=PolicyOutcome.ALLOW, reason="")

        # Collect all non-empty reasons regardless of outcome
        reasons = [d.reason for d in decisions if d.reason]

        # DENY wins immediately
        deny_decisions = [d for d in decisions if d.outcome == PolicyOutcome.DENY]
        if deny_decisions:
            merged_meta: dict[str, str] = {}
            for d in deny_decisions:
                merged_meta.update(d.metadata)
            return PolicyDecision(
                outcome=PolicyOutcome.DENY,
                reason="; ".join(reasons),
                metadata=merged_meta,
            )

        # Most-restrictive outcome among remaining
        winner = max(decisions, key=lambda d: _OUTCOME_ORDER.index(d.outcome))

        merged_meta = {}
        for d in decisions:
            merged_meta.update(d.metadata)

        return PolicyDecision(
            outcome=winner.outcome,
            reason="; ".join(reasons),
            metadata=merged_meta,
        )


__all__ = [
    "AlwaysAllowGate",
    "CompositeGate",
]
