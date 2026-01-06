"""ApprovalChain — sequential multi-step approval orchestration."""

from __future__ import annotations

from lexigram.logging import get_logger
from lexigram.workflow.approval.models import (
    ApprovalPolicy,
    ApprovalStatus,
    ApprovalStep,
)

logger = get_logger(__name__)

__all__ = ["ApprovalChain"]


class ApprovalChain:
    """Orchestrates a sequence of :class:`~lexigram.workflow.approval.ApprovalStep`
    objects under a configurable :class:`~lexigram.workflow.approval.ApprovalPolicy`.

    Each step is executed in registration order.  Steps whose *condition*
    returns ``False`` are skipped.  The final outcome is computed from the
    collected per-step statuses according to the active policy.

    Example::

        from lexigram.workflow.approval import ApprovalChain, ApprovalStep, ApprovalPolicy

        chain = ApprovalChain(policy=ApprovalPolicy.ALL)
        chain.add_step(ApprovalStep(
            name="manager_review",
            approver=manager_service.approve,
        ))
        chain.add_step(ApprovalStep(
            name="finance_review",
            approver=finance_service.approve,
            condition=lambda: request.amount > 10_000,
        ))

        approved, results = await chain.execute()
        if approved:
            await order_service.confirm(request_id)

    Args:
        policy: Determines the approval outcome based on individual step
            results.  Defaults to :attr:`~ApprovalPolicy.ALL`.
    """

    def __init__(self, policy: ApprovalPolicy = ApprovalPolicy.ALL) -> None:
        self._policy = policy
        self._steps: list[ApprovalStep] = []

    # ------------------------------------------------------------------
    # Step registration
    # ------------------------------------------------------------------

    def add_step(self, step: ApprovalStep) -> None:
        """Append *step* to the chain.

        Args:
            step: The approval step to add.
        """
        self._steps.append(step)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self) -> tuple[bool, dict[str, ApprovalStatus]]:
        """Run all steps in registration order and compute the final outcome.

        Steps whose *condition* returns ``False`` receive status
        :attr:`~ApprovalStatus.SKIPPED` and do not influence the policy
        outcome.

        Returns:
            A 2-tuple of:
            - ``bool``: ``True`` when the chain is approved per the policy.
            - ``dict[str, ApprovalStatus]``: Per-step status keyed by step name.
        """
        results: dict[str, ApprovalStatus] = {}

        for step in self._steps:
            if step.condition is not None:
                should_run = await step.condition()
                if not should_run:
                    results[step.name] = ApprovalStatus.SKIPPED
                    logger.debug(
                        "approval_step.skipped",
                        step=step.name,
                    )
                    continue

            logger.debug("approval_step.started", step=step.name)
            approved = await step.approver()
            status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
            results[step.name] = status
            logger.info(
                "approval_step.completed",
                step=step.name,
                status=status,
            )

        outcome = self._evaluate_policy(results)
        logger.info(
            "approval_chain.completed",
            policy=self._policy,
            approved=outcome,
            results={k: v.value for k, v in results.items()},
        )
        return outcome, results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evaluate_policy(self, results: dict[str, ApprovalStatus]) -> bool:
        """Apply the configured policy to determine the final outcome.

        Only :attr:`~ApprovalStatus.APPROVED` and
        :attr:`~ApprovalStatus.REJECTED` statuses are counted; skipped steps
        are neutral.

        Args:
            results: Per-step status map produced by :meth:`execute`.

        Returns:
            ``True`` when the policy is satisfied; ``False`` otherwise.
        """
        non_skipped = {
            name: status
            for name, status in results.items()
            if status != ApprovalStatus.SKIPPED
        }
        if not non_skipped:
            # No runnable steps — treat as approved (vacuously true).
            return True

        approved_count = sum(
            1 for s in non_skipped.values() if s == ApprovalStatus.APPROVED
        )
        total = len(non_skipped)

        if self._policy == ApprovalPolicy.ALL:
            return approved_count == total
        if self._policy == ApprovalPolicy.ANY:
            return approved_count >= 1
        if self._policy == ApprovalPolicy.MAJORITY:
            return approved_count > total / 2
        return False  # pragma: no cover — exhaustive StrEnum
