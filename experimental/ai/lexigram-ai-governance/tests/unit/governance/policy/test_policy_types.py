"""Unit tests for lexigram.ai.governance.policy.types."""

from __future__ import annotations

from lexigram.ai.governance.policy import (
    GovernanceContext,
    PolicyEffect,
    PolicyRule,
    PolicyScope,
    PolicyViolation,
)


class TestPolicyRule:
    def test_matches_model_pattern(self) -> None:
        rule = PolicyRule(
            scope=PolicyScope.MODEL,
            effect=PolicyEffect.DENY,
            condition={"model_pattern": "gpt-4o"},
        )
        
        context = GovernanceContext(model="gpt-4o", provider="openai")
        
        matches = _match_model_rule(rule, context)
        assert matches is True

    def test_matches_model_pattern_no_match(self) -> None:
        rule = PolicyRule(
            scope=PolicyScope.MODEL,
            effect=PolicyEffect.DENY,
            condition={"model_pattern": "gpt-4o"},
        )
        
        context = GovernanceContext(model="claude-3", provider="anthropic")
        
        matches = _match_model_rule(rule, context)
        assert matches is False

    def test_matches_wildcard_model(self) -> None:
        rule = PolicyRule(
            scope=PolicyScope.MODEL,
            effect=PolicyEffect.ALLOW,
            condition={"model_pattern": "gpt-4*"},
        )
        
        assert _match_model_rule(rule, GovernanceContext(model="gpt-4o")) is True
        assert _match_model_rule(rule, GovernanceContext(model="gpt-4o-mini")) is True
        assert _match_model_rule(rule, GovernanceContext(model="gpt-3.5-turbo")) is False

    def test_matches_cost_limit(self) -> None:
        rule = PolicyRule(
            scope=PolicyScope.COST,
            effect=PolicyEffect.DENY,
            condition={"max_cost": 0.50},
        )
        
        context = GovernanceContext(model="gpt-4o", estimated_cost=0.75)
        
        matches = _match_cost_rule(rule, context)
        assert matches is True

    def test_matches_cost_limit_within_limit(self) -> None:
        rule = PolicyRule(
            scope=PolicyScope.COST,
            effect=PolicyEffect.ALLOW,
            condition={"max_cost": 0.50},
        )
        
        context = GovernanceContext(model="gpt-4o", estimated_cost=0.25)
        
        matches = _match_cost_rule(rule, context)
        assert matches is False

    def test_matches_guardrail_requirement(self) -> None:
        rule = PolicyRule(
            scope=PolicyScope.GUARDRAIL,
            effect=PolicyEffect.DENY,
            condition={"required": ["pii_filter", "content_filter"]},
        )
        
        context = GovernanceContext(
            model="gpt-4o",
            metadata={"guardrails": ["content_filter", "pii_filter"]},
        )
        
        matches = _match_guardrail_rule(rule, context)
        assert matches is True

    def test_matches_guardrail_requirement_partial(self) -> None:
        rule = PolicyRule(
            scope=PolicyScope.GUARDRAIL,
            effect=PolicyEffect.DENY,
            condition={"required": ["pii_filter", "content_filter"]},
        )
        
        context = GovernanceContext(
            model="gpt-4o",
            metadata={"guardrails": ["content_filter"]},
        )
        
        matches = _match_guardrail_rule(rule, context)
        assert matches is False

    def test_rule_with_roles(self) -> None:
        rule = PolicyRule(
            scope=PolicyScope.MODEL,
            effect=PolicyEffect.DENY,
            condition={"model_pattern": "gpt-4*"},
            roles=["admin", "developer"],
        )
        
        admin_context = GovernanceContext(model="gpt-4o", role="admin")
        user_context = GovernanceContext(model="gpt-4o", role="user")
        
        assert _match_model_rule(rule, admin_context) is True
        assert _match_model_rule(rule, user_context) is False


class TestGovernanceContext:
    def test_context_construction(self) -> None:
        context = GovernanceContext(
            model="gpt-4o",
            provider="openai",
            role="api_user",
            tenant_id="tenant-123",
            estimated_cost=0.05,
            data_classification="internal",
            metadata={"source": "api"},
        )
        
        assert context.model == "gpt-4o"
        assert context.provider == "openai"
        assert context.role == "api_user"
        assert context.tenant_id == "tenant-123"
        assert context.estimated_cost == 0.05
        assert context.data_classification == "internal"
        assert context.metadata == {"source": "api"}

    def test_context_defaults(self) -> None:
        context = GovernanceContext(model="gpt-4o")
        
        assert context.model == "gpt-4o"
        assert context.provider == ""
        assert context.role == ""
        assert context.tenant_id is None
        assert context.estimated_cost == 0.0
        assert context.data_classification == "public"
        assert context.metadata == {}


class TestPolicyViolation:
    def test_violation_creation(self) -> None:
        context = GovernanceContext(
            model="gpt-4o",
            provider="openai",
            role="user",
            estimated_cost=1.0,
        )
        
        violation = PolicyViolation(
            policy_name="cost-policy",
            reason="Estimated cost exceeds $0.50 limit",
            context=context,
        )
        
        assert violation.policy_name == "cost-policy"
        assert violation.reason == "Estimated cost exceeds $0.50 limit"
        assert violation.context.model == "gpt-4o"
        assert violation.context.estimated_cost == 1.0

    def test_violation_str_representation(self) -> None:
        context = GovernanceContext(model="gpt-4o", role="admin")
        
        violation = PolicyViolation(
            policy_name="model-deny",
            reason="Restricted model",
            context=context,
        )
        
        assert "model-deny" in str(violation)
        assert "Restricted model" in str(violation)


# Helper functions for rule matching logic (used in tests above)


def _match_model_rule(rule: PolicyRule, context: GovernanceContext) -> bool:
    if rule.scope != PolicyScope.MODEL:
        return False
    if rule.roles and context.role not in rule.roles:
        return False
    pattern = rule.condition.get("model_pattern", "")
    if not pattern:
        return False
    if "*" in pattern:
        prefix = pattern.replace("*", "")
        return context.model.startswith(prefix)
    return context.model == pattern


def _match_cost_rule(rule: PolicyRule, context: GovernanceContext) -> bool:
    if rule.scope != PolicyScope.COST:
        return False
    max_cost = rule.condition.get("max_cost")
    if max_cost is None:
        return False
    return context.estimated_cost > max_cost


def _match_guardrail_rule(rule: PolicyRule, context: GovernanceContext) -> bool:
    if rule.scope != PolicyScope.GUARDRAIL:
        return False
    required = rule.condition.get("required", [])
    if not required:
        return False
    present = context.metadata.get("guardrails", [])
    return all(r in present for r in required)
