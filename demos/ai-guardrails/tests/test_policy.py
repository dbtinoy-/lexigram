"""Tests for the acts registry and policy toggle."""

from __future__ import annotations

from guard_gate.acts import ACTS, ALLOWED_MODEL, COST_PER_TURN
from guard_gate.policy import PolicyToggle


class TestActs:
    def test_five_acts_registered(self) -> None:
        assert set(ACTS) == {"injection", "pii", "length", "model", "budget"}

    def test_model_act_uses_restricted_model(self) -> None:
        assert ACTS["model"].model != ALLOWED_MODEL

    def test_length_act_exceeds_limit(self) -> None:
        assert len(ACTS["length"].text) > 500

    def test_pii_act_contains_email(self) -> None:
        assert "@" in ACTS["pii"].text


class TestPolicyToggle:
    def test_enabled_by_default(self) -> None:
        assert PolicyToggle().enabled is True

    def test_set_flips_state(self) -> None:
        toggle = PolicyToggle()
        toggle.set(False)
        assert toggle.enabled is False
        toggle.set(True)
        assert toggle.enabled is True

    def test_budget_math_constant(self) -> None:
        # three costed turns fit; the fourth check must fail
        assert round(COST_PER_TURN * 3, 2) <= 0.50 < round(COST_PER_TURN * 4, 2)
