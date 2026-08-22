"""Service-level tests for the guarded pipeline (resolved from boot)."""

from __future__ import annotations

import pytest

from guard_gate.repository.acts import ACTS, COST_PER_TURN, ALLOWED_MODEL


@pytest.fixture
async def assistant(app):
    from guard_gate.services.guarded_assistant import GuardedAssistant

    return await app.container.resolve(GuardedAssistant)


class TestFiveActs:
    async def test_injection_blocked(self, assistant) -> None:
        act = ACTS["injection"]
        outcome = await assistant.handle("alice", act.text, act.model)

        assert outcome.kind == "blocked"
        assert outcome.reply is None
        assert outcome.reason

    async def test_pii_redacted_end_to_end(self, assistant) -> None:
        act = ACTS["pii"]
        outcome = await assistant.handle("alice", act.text, act.model)

        assert outcome.kind == "redacted"
        assert outcome.reply is not None
        assert "[REDACTED:EMAIL]" in outcome.reply
        assert "jane.doe@example.com" not in outcome.reply

    async def test_length_act_blocked(self, assistant) -> None:
        act = ACTS["length"]
        outcome = await assistant.handle("alice", act.text, act.model)

        assert outcome.kind == "blocked"

    async def test_restricted_model_denied(self, assistant) -> None:
        act = ACTS["model"]
        outcome = await assistant.handle("alice", act.text, act.model)

        assert outcome.kind == "denied_model"
        assert "restricted" in (outcome.reason or "")

    async def test_budget_exhaustion_after_three_costed_turns(
        self, assistant,
    ) -> None:
        for _ in range(3):
            ok = await assistant.handle(
                "bob", "Tell me about shipping.", ALLOWED_MODEL,
            )
            assert ok.kind == "pass"

        drained = await assistant.handle(
            "bob", ACTS["budget"].text, ACTS["budget"].model,
        )
        assert drained.kind == "denied_budget"
        assert drained.reason == "monthly budget exhausted"
        assert drained.remaining_budget == round(0.50 - 3 * COST_PER_TURN, 2)


class TestLedgerAndBypass:
    async def test_spent_tracks_only_costed_turns(self, assistant) -> None:
        spent_before = assistant.remaining
        await assistant.handle(
            "carol", ACTS["injection"].text, ALLOWED_MODEL,
        )  # blocked: free
        assert assistant.remaining == spent_before

        await assistant.handle("carol", "Tell me about returns.", ALLOWED_MODEL)
        assert assistant.remaining == round(spent_before - COST_PER_TURN, 2)

    async def test_policy_off_bypasses_everything(self, assistant) -> None:
        toggle = assistant.toggle
        toggle.set(False)
        try:
            outcome = await assistant.handle(
                "dave", ACTS["injection"].text, ACTS["model"].model,
            )
            assert outcome.kind == "pass"  # raw canned reply, no denial
        finally:
            toggle.set(True)
