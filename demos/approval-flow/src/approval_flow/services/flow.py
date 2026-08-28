"""Interactive approval flow backed by Lexigram workflow primitives."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from approval_flow.config import ApprovalFlowConfig
from lexigram.workflow.approval import (
    ApprovalChain,
    ApprovalPolicy,
    ApprovalStep,
)
from lexigram.workflow.state import State, StateError, StateMachine, Transition


class ApprovalFlowService:
    """Keep one purchase request moving through a real Lexigram state machine.

    The state machine is deliberately rebuilt for a new request and the
    service keeps a small browser-facing event ledger. Approval-chain preview
    uses the package's multi-step ``ApprovalChain`` without hiding the
    interactive state transitions from the user.
    """

    def __init__(self, config: ApprovalFlowConfig) -> None:
        self._config = config
        self._actor = "requester"
        self._request = {
            "title": config.initial_request,
            "amount": config.initial_amount,
            "owner": "Maya Chen",
        }
        self._history: list[dict[str, Any]] = []
        self._machine = self._new_machine()

    def _new_machine(self) -> StateMachine:
        states = [
            State(
                "draft",
                transitions={"submit": Transition("submit", "manager_review")},
            ),
            State(
                "manager_review",
                transitions={
                    "approve_manager": Transition("approve_manager", "finance_review"),
                    "reject_manager": Transition("reject_manager", "rejected"),
                },
            ),
            State(
                "finance_review",
                transitions={
                    "approve_finance": Transition("approve_finance", "approved"),
                    "reject_finance": Transition("reject_finance", "rejected"),
                },
            ),
            State(
                "approved",
                transitions={
                    "rollback": Transition("rollback", "manager_review"),
                    "reset": Transition("reset", "draft"),
                },
            ),
            State(
                "rejected",
                transitions={
                    "retry": Transition("retry", "manager_review"),
                    "reset": Transition("reset", "draft"),
                },
            ),
        ]
        machine = StateMachine(states=states, initial_state="draft")
        self._history = []
        return machine

    def snapshot(self) -> dict[str, Any]:
        state = self._machine.current_state
        return {
            "request": self._request,
            "state": state,
            "version": self._machine.version,
            "available_events": self._events_for(state),
            "history": list(self._history),
            "steps": self._step_statuses(),
            "policy": ApprovalPolicy.ALL.value,
        }

    async def create_request(
        self, title: str, amount: int, owner: str
    ) -> dict[str, Any]:
        title = title.strip()
        if not title:
            raise ValueError("Request title is required")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        self._request = {
            "title": title,
            "amount": amount,
            "owner": owner.strip() or "Requester",
        }
        self._machine = self._new_machine()
        return self.snapshot()

    async def transition(self, event: str, actor: str) -> dict[str, Any]:
        state_before = self._machine.current_state
        if not self._machine.can_transition(event):
            raise StateError(event, state_before)
        state_after = await self._machine.transition(event)
        self._history.append(
            {
                "version": self._machine.version,
                "from_state": state_before,
                "event": event,
                "to_state": state_after,
                "actor": actor.strip() or "operator",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        return self.snapshot()

    async def policy_preview(
        self,
        manager_approved: bool = True,
        finance_approved: bool = True,
    ) -> dict[str, Any]:
        """Run the package ApprovalChain independently as a policy preview."""

        async def manager_gate() -> bool:
            return manager_approved

        async def finance_gate() -> bool:
            return finance_approved

        chain = ApprovalChain(policy=ApprovalPolicy.ALL)
        chain.add_step(
            ApprovalStep("manager", manager_gate, metadata={"role": "manager"})
        )
        chain.add_step(
            ApprovalStep("finance", finance_gate, metadata={"role": "finance"})
        )
        approved, results = await chain.execute()
        return {
            "approved": approved,
            "policy": ApprovalPolicy.ALL.value,
            "steps": {name: status.value for name, status in results.items()},
        }

    def _events_for(self, state: str) -> list[dict[str, str]]:
        return {
            "draft": [{"event": "submit", "label": "Submit for review"}],
            "manager_review": [
                {"event": "approve_manager", "label": "Manager approve"},
                {"event": "reject_manager", "label": "Manager reject"},
            ],
            "finance_review": [
                {"event": "approve_finance", "label": "Finance approve"},
                {"event": "reject_finance", "label": "Finance reject"},
            ],
            "approved": [
                {"event": "rollback", "label": "Rollback / compensate"},
                {"event": "reset", "label": "Start another request"},
            ],
            "rejected": [
                {"event": "retry", "label": "Retry approval"},
                {"event": "reset", "label": "Start another request"},
            ],
        }[state]

    def _step_statuses(self) -> list[dict[str, str]]:
        state = self._machine.current_state
        manager = (
            "approved"
            if state in {"finance_review", "approved"}
            else "rejected"
            if state == "rejected"
            else "pending"
        )
        finance = (
            "approved"
            if state == "approved"
            else "rejected"
            if state == "rejected"
            and any(item["event"] == "reject_finance" for item in self._history)
            else "pending"
        )
        return [
            {"name": "manager", "label": "Manager review", "status": manager},
            {"name": "finance", "label": "Finance review", "status": finance},
        ]


__all__ = ["ApprovalFlowService"]
