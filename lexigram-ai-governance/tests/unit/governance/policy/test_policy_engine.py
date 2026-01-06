"""Tests for PolicyEngine — declarative rule evaluation.

Covers all four policy scopes (MODEL, COST, GUARDRAIL, DATA_CLASSIFICATION),
role filtering, priority ordering, and the Result-based return contract.
"""

from __future__ import annotations

import pytest

from lexigram.ai.governance.policy.engine import PolicyEngine
from lexigram.ai.governance.policy.store import PolicyStore
from lexigram.ai.governance.policy.types import (
    GovernanceContext,
    Policy,
    PolicyDecision,
    PolicyEffect,
    PolicyRule,
    PolicyScope,
    PolicyViolation,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deny_model(pattern: str, roles: list[str] | None = None) -> PolicyRule:
    return PolicyRule(
        scope=PolicyScope.MODEL,
        effect=PolicyEffect.DENY,
        condition={"model_pattern": pattern},
        roles=roles or [],
    )


def _deny_cost(max_cost: float, roles: list[str] | None = None) -> PolicyRule:
    return PolicyRule(
        scope=PolicyScope.COST,
        effect=PolicyEffect.DENY,
        condition={"max_cost": max_cost},
        roles=roles or [],
    )


def _deny_guardrail(required: list[str]) -> PolicyRule:
    return PolicyRule(
        scope=PolicyScope.GUARDRAIL,
        effect=PolicyEffect.DENY,
        condition={"required": required},
    )


def _deny_classification(classification: str) -> PolicyRule:
    return PolicyRule(
        scope=PolicyScope.DATA_CLASSIFICATION,
        effect=PolicyEffect.DENY,
        condition={"classification": classification},
    )


async def _make_engine(policies: list[Policy]) -> PolicyEngine:
    store = PolicyStore()
    for policy in policies:
        await store.add_policy(policy)
    return PolicyEngine(store=store)


def _ctx(
    model: str = "gpt-4",
    role: str = "api_user",
    estimated_cost: float = 0.0,
    data_classification: str = "public",
    active_guardrails: list[str] | None = None,
) -> GovernanceContext:
    metadata: dict = {}
    if active_guardrails is not None:
        metadata["active_guardrails"] = active_guardrails
    return GovernanceContext(
        model=model,
        role=role,
        estimated_cost=estimated_cost,
        data_classification=data_classification,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# No-policy / allow-all cases
# ---------------------------------------------------------------------------


class TestPolicyEngineAllowCases:
    @pytest.mark.asyncio
    async def test_empty_store_allows_any_request(self) -> None:
        engine = await _make_engine([])
        result = await engine.evaluate(_ctx())
        assert result.is_ok()
        decision = result.unwrap()
        assert isinstance(decision, PolicyDecision)
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_policy_with_only_allow_rules_permits_request(self) -> None:
        allow_rule = PolicyRule(
            scope=PolicyScope.MODEL,
            effect=PolicyEffect.ALLOW,
            condition={"model_pattern": "*"},
        )
        policy = Policy(name="allow-all", rules=[allow_rule])
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(model="gpt-4"))
        assert result.is_ok()
        assert result.unwrap().allowed is True

    @pytest.mark.asyncio
    async def test_disabled_policy_is_ignored(self) -> None:
        policy = Policy(
            name="block-all",
            enabled=False,
            rules=[_deny_model("*")],
        )
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx())
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_returns_ok_type_is_result(self) -> None:
        engine = await _make_engine([])
        result = await engine.evaluate(_ctx())
        assert result.is_ok()
        assert not result.is_err()
        decision = result.unwrap()
        assert decision.allowed is True


# ---------------------------------------------------------------------------
# MODEL scope
# ---------------------------------------------------------------------------


class TestModelScopePolicy:
    @pytest.mark.asyncio
    async def test_denies_exact_model_match(self) -> None:
        policy = Policy(name="block-gpt4", rules=[_deny_model("gpt-4")])
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(model="gpt-4"))
        assert result.is_err()
        violation = result.unwrap_err()
        assert isinstance(violation, PolicyViolation)
        assert violation.policy_name == "block-gpt4"

    @pytest.mark.asyncio
    async def test_denies_wildcard_prefix_pattern(self) -> None:
        policy = Policy(name="block-gpt-series", rules=[_deny_model("gpt-*")])
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(model="gpt-3.5-turbo"))
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_allows_model_not_matching_pattern(self) -> None:
        policy = Policy(name="block-gpt-series", rules=[_deny_model("gpt-*")])
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(model="claude-3-sonnet"))
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_violation_contains_context(self) -> None:
        policy = Policy(name="block-gpt4", rules=[_deny_model("gpt-4")])
        engine = await _make_engine([policy])
        ctx = _ctx(model="gpt-4", role="free_tier")
        result = await engine.evaluate(ctx)
        violation = result.unwrap_err()
        assert violation.context is ctx

    @pytest.mark.asyncio
    async def test_violation_reason_mentions_model(self) -> None:
        policy = Policy(name="block-gpt4", rules=[_deny_model("gpt-*")])
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(model="gpt-4o"))
        violation = result.unwrap_err()
        assert "gpt-4o" in violation.reason
        assert "gpt-*" in violation.reason


# ---------------------------------------------------------------------------
# COST scope
# ---------------------------------------------------------------------------


class TestCostScopePolicy:
    @pytest.mark.asyncio
    async def test_denies_when_cost_exceeds_limit(self) -> None:
        policy = Policy(name="cost-cap", rules=[_deny_cost(0.10)])
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(estimated_cost=0.11))
        assert result.is_err()
        violation = result.unwrap_err()
        assert violation.policy_name == "cost-cap"
        assert "cost" in violation.reason.lower()

    @pytest.mark.asyncio
    async def test_allows_when_cost_at_limit(self) -> None:
        policy = Policy(name="cost-cap", rules=[_deny_cost(0.10)])
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(estimated_cost=0.10))
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_allows_when_cost_below_limit(self) -> None:
        policy = Policy(name="cost-cap", rules=[_deny_cost(0.10)])
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(estimated_cost=0.05))
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_cost_rule_missing_max_cost_never_matches(self) -> None:
        rule = PolicyRule(
            scope=PolicyScope.COST,
            effect=PolicyEffect.DENY,
            condition={},  # no max_cost key
        )
        policy = Policy(name="bad-cost-rule", rules=[rule])
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(estimated_cost=999.0))
        assert result.is_ok()


# ---------------------------------------------------------------------------
# GUARDRAIL scope
# ---------------------------------------------------------------------------


class TestGuardrailScopePolicy:
    @pytest.mark.asyncio
    async def test_denies_when_required_guardrail_missing(self) -> None:
        policy = Policy(
            name="require-pii-guard",
            rules=[_deny_guardrail(["pii_guard"])],
        )
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(active_guardrails=[]))
        assert result.is_err()
        violation = result.unwrap_err()
        assert "pii_guard" in violation.reason

    @pytest.mark.asyncio
    async def test_allows_when_all_required_guardrails_present(self) -> None:
        policy = Policy(
            name="require-pii-guard",
            rules=[_deny_guardrail(["pii_guard", "injection_guard"])],
        )
        engine = await _make_engine([policy])
        result = await engine.evaluate(
            _ctx(active_guardrails=["pii_guard", "injection_guard", "extra_guard"])
        )
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_denies_when_only_partial_guardrails_present(self) -> None:
        policy = Policy(
            name="require-both",
            rules=[_deny_guardrail(["pii_guard", "injection_guard"])],
        )
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(active_guardrails=["pii_guard"]))
        assert result.is_err()
        assert "injection_guard" in result.unwrap_err().reason

    @pytest.mark.asyncio
    async def test_guardrail_reason_lists_missing_guards(self) -> None:
        policy = Policy(
            name="require-multiple",
            rules=[_deny_guardrail(["g1", "g2", "g3"])],
        )
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(active_guardrails=["g1"]))
        reason = result.unwrap_err().reason
        assert "g2" in reason
        assert "g3" in reason


# ---------------------------------------------------------------------------
# DATA_CLASSIFICATION scope
# ---------------------------------------------------------------------------


class TestDataClassificationScopePolicy:
    @pytest.mark.asyncio
    async def test_denies_pii_data_classification(self) -> None:
        policy = Policy(
            name="no-pii-external",
            rules=[_deny_classification("pii")],
        )
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(data_classification="pii"))
        assert result.is_err()
        assert "pii" in result.unwrap_err().reason

    @pytest.mark.asyncio
    async def test_allows_public_data_when_pii_denied(self) -> None:
        policy = Policy(
            name="no-pii-external",
            rules=[_deny_classification("pii")],
        )
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(data_classification="public"))
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_denies_confidential_classification(self) -> None:
        policy = Policy(
            name="no-confidential",
            rules=[_deny_classification("confidential")],
        )
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(data_classification="confidential"))
        assert result.is_err()


# ---------------------------------------------------------------------------
# Role filtering
# ---------------------------------------------------------------------------


class TestRoleFiltering:
    @pytest.mark.asyncio
    async def test_rule_with_matching_role_applies(self) -> None:
        rule = _deny_model("gpt-4", roles=["free_tier"])
        policy = Policy(name="free-tier-block", rules=[rule])
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(model="gpt-4", role="free_tier"))
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_rule_with_non_matching_role_is_skipped(self) -> None:
        rule = _deny_model("gpt-4", roles=["free_tier"])
        policy = Policy(name="free-tier-block", rules=[rule])
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(model="gpt-4", role="admin"))
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_rule_with_empty_roles_applies_to_all(self) -> None:
        rule = _deny_model("gpt-4", roles=[])  # empty = all roles
        policy = Policy(name="block-all-roles", rules=[rule])
        engine = await _make_engine([policy])
        for role in ("free_tier", "admin", "service_account"):
            result = await engine.evaluate(_ctx(model="gpt-4", role=role))
            assert result.is_err(), f"Expected deny for role={role}"

    @pytest.mark.asyncio
    async def test_policy_without_matching_role_in_any_rule_is_filtered_out(self) -> None:
        rule = _deny_model("gpt-4", roles=["free_tier"])
        policy = Policy(name="free-tier-only", rules=[rule])
        engine = await _make_engine([policy])
        # PolicyStore.get_policies filters by scope=role; role "admin" isn't in
        # the rule's roles list, but the rule.roles check inside evaluate() also
        # skips the rule independently — so admin should be allowed.
        result = await engine.evaluate(_ctx(model="gpt-4", role="admin"))
        assert result.is_ok()


# ---------------------------------------------------------------------------
# Priority ordering and short-circuit
# ---------------------------------------------------------------------------


class TestPriorityAndShortCircuit:
    @pytest.mark.asyncio
    async def test_first_deny_rule_short_circuits(self) -> None:
        policy = Policy(
            name="multi-rule",
            rules=[
                _deny_model("gpt-4"),
                _deny_cost(0.01),  # should never be reached
            ],
        )
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx(model="gpt-4", estimated_cost=999.9))
        assert result.is_err()
        violation = result.unwrap_err()
        # Only the model violation reason should be present
        assert "gpt-4" in violation.reason

    @pytest.mark.asyncio
    async def test_lower_priority_policy_evaluated_first(self) -> None:
        allow_policy = Policy(
            name="allow-all",
            priority=10,
            rules=[
                PolicyRule(
                    scope=PolicyScope.MODEL,
                    effect=PolicyEffect.ALLOW,
                    condition={"model_pattern": "*"},
                )
            ],
        )
        deny_policy = Policy(
            name="deny-gpt4",
            priority=5,  # evaluated first
            rules=[_deny_model("gpt-4")],
        )
        engine = await _make_engine([allow_policy, deny_policy])
        result = await engine.evaluate(_ctx(model="gpt-4"))
        # deny_policy runs first (priority=5) → DENY
        assert result.is_err()
        assert result.unwrap_err().policy_name == "deny-gpt4"

    @pytest.mark.asyncio
    async def test_multiple_policies_all_allow_returns_ok(self) -> None:
        policies = [
            Policy(name=f"policy-{i}", rules=[_deny_model("o1-preview")], priority=i)
            for i in range(3)
        ]
        engine = await _make_engine(policies)
        result = await engine.evaluate(_ctx(model="gpt-4"))
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_err_is_of_type_policy_violation(self) -> None:
        policy = Policy(name="block", rules=[_deny_model("*")])
        engine = await _make_engine([policy])
        result = await engine.evaluate(_ctx())
        assert result.is_err()
        assert isinstance(result.unwrap_err(), PolicyViolation)
