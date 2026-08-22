"""The guarded request pipeline — gates, guards, cost, ledger."""

from __future__ import annotations

from dataclasses import dataclass

from guard_gate.repository.acts import PROVIDER
from guard_gate.services.policy import PolicyToggle
from lexigram.ai.governance.audit import AIAuditStore
from lexigram.ai.governance.audit.models import AuditQuery
from lexigram.contracts.ai.governance import AIGovernanceProtocol
from lexigram.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class Outcome:
    """Value result of one handled request — denial-as-data."""

    kind: str  # pass|blocked|redacted|denied_model|denied_budget
    reply: str | None = None
    reason: str | None = None
    remaining_budget: float | None = None


class GuardedAssistant:
    """One entry point: gate → budget → guards → reply → output pass → cost."""

    def __init__(
        self,
        pipeline,
        governance: AIGovernanceProtocol,
        audit_store: AIAuditStore,
        monthly_budget: float,
        restricted_models: list[str],
        toggle: PolicyToggle,
        cost_per_turn: float,
    ) -> None:
        self._pipeline = pipeline
        self._governance = governance
        self._audit_store = audit_store
        self.monthly_budget = monthly_budget
        self._restricted = list(restricted_models)
        self.toggle = toggle  # shared instance for tests/UI
        self.cost_per_turn = cost_per_turn

    @property
    def remaining(self) -> float:
        """Budget minus locally-charged spend (manager exposes no getter)."""
        return round(self.monthly_budget - self._spent(), 2)

    def _spent(self) -> float:
        """Charged turns this process has completed."""
        return getattr(self, "_charged", 0)

    async def handle(self, user_id: str, text: str, model: str) -> Outcome:
        """Run one request through the full protected path."""
        if not self.toggle.enabled:
            return Outcome("pass", _canned(text))

        if not await self._governance.check_request(model, PROVIDER, user_id):
            reason = (
                f"restricted model: {model}"
                if model in self._restricted
                else "policy denied"
            )
            return Outcome("denied_model", reason=reason)

        if not await self._governance.check_budget(
            self.cost_per_turn,
            user_id,
        ):
            return Outcome(
                "denied_budget",
                reason="monthly budget exhausted",
                remaining_budget=self.remaining,
            )

        checked_result = await self._pipeline.check_input(
            text,
            messages=[],
            metadata={},
        )
        if checked_result.is_err():
            return Outcome("blocked", reason=str(checked_result.unwrap_err()))
        checked = checked_result.unwrap()
        if checked.blocked:
            blocker = checked.blocking_result
            details = getattr(blocker, "details", {}) or {}
            raw_reason = details.get("reason") or getattr(blocker, "reason", "")
            reason = str(raw_reason or "")
            return Outcome("blocked", reason=reason)

        working_text = checked.final_content or text
        reply_text = _canned(working_text)
        outbound_result = await self._pipeline.check_output(
            reply_text,
            original_input=text,
            metadata={},
        )
        if outbound_result.is_err():
            return Outcome(
                "redacted",
                reply=reply_text,
                reason=str(outbound_result.unwrap_err()),
            )
        outbound = outbound_result.unwrap()
        final_reply = outbound.final_content or reply_text

        await self._governance.track_cost(self.cost_per_turn, model, user_id)
        self._charged = self._spent() + self.cost_per_turn

        kind = "redacted" if "[REDACTED:" in final_reply else "pass"
        logger.info("guard_outcome", kind=kind, model=model, user_id=user_id)
        return Outcome(kind, final_reply, remaining_budget=self.remaining)

    async def audit_rows(self, limit: int = 50) -> list[dict]:
        """Recent audit events, serialized for the console table."""
        events = await self._audit_store.query(AuditQuery(limit=limit))
        return [
            {
                "event_type": _event_name(e),
                "status": e.status,
                "model": e.model,
                "cost": e.cost,
            }
            for e in events
        ]


def _event_name(event) -> str:
    """Normalize enum-or-string event types to their plain value."""
    value = event.event_type
    return str(value.value) if hasattr(value, "value") else str(value)


def _canned(text: str) -> str:
    """Deterministic demo reply echoing the (possibly redacted) input."""
    trimmed = " ".join(text.split())
    snippet = trimmed[:80]
    return f"(demo reply) You asked about: {snippet}"
