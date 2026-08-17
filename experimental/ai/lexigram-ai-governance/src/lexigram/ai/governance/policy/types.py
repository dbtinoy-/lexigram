"""Governance policy domain types.

Declarative policy rules that gate AI usage by role, cost, required
guardrails, and data classification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PolicyEffect(StrEnum):
    """Whether a policy allows or denies the matched request."""

    ALLOW = "allow"
    DENY = "deny"


class PolicyScope(StrEnum):
    """Dimension a policy rule applies to."""

    MODEL = "model"
    COST = "cost"
    GUARDRAIL = "guardrail"
    DATA_CLASSIFICATION = "data_classification"


@dataclass
class PolicyRule:
    """A single rule within a :class:`Policy`.

    Attributes:
        scope: The dimension this rule applies to.
        effect: Whether the rule allows or denies matching requests.
        condition: Dict of condition parameters (scope-specific).
            Examples:
            - ``{"model_pattern": "gpt-4*"}`` for MODEL scope.
            - ``{"max_cost": 0.50}`` for COST scope.
            - ``{"required": ["pii_filter"]}`` for GUARDRAIL scope.
            - ``{"classification": "public"}`` for DATA_CLASSIFICATION.
        roles: Roles this rule applies to; empty list means all roles.
    """

    scope: PolicyScope
    effect: PolicyEffect
    condition: dict[str, Any] = field(default_factory=dict)
    roles: list[str] = field(default_factory=list)


@dataclass
class Policy:
    """A named, versioned governance policy composed of rules.

    Attributes:
        name: Unique policy identifier.
        description: Human-readable description.
        rules: Ordered list of rules; first match wins.
        priority: Lower value = evaluated first when multiple policies match.
        enabled: Whether the policy is currently active.
    """

    name: str
    description: str = ""
    rules: list[PolicyRule] = field(default_factory=list)
    priority: int = 100
    enabled: bool = True


@dataclass
class GovernanceContext:
    """Context passed to the policy engine for evaluation.

    Attributes:
        model: Model identifier being requested.
        provider: Provider name.
        role: Caller role (e.g. ``"api_user"``, ``"admin"``).
        tenant_id: Tenant / organisation identifier.
        estimated_cost: Estimated cost of the request in USD.
        data_classification: Data classification label (e.g. ``"pii"``).
        metadata: Additional context key/value pairs.
    """

    model: str
    provider: str = ""
    role: str = ""
    tenant_id: str | None = None
    estimated_cost: float = 0.0
    data_classification: str = "public"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyDecision:
    """Result of a :class:`~engine.PolicyEngine` evaluation.

    Attributes:
        allowed: Whether the request is permitted.
        matched_policy: Name of the first policy that produced a DENY, or
            ``None`` when allowed.
        reason: Human-readable reason string.
    """

    allowed: bool
    matched_policy: str | None = None
    reason: str = ""


@dataclass
class PolicyViolation:
    """Domain error returned when a policy denies a request.

    Attributes:
        policy_name: Name of the violated policy.
        reason: Reason the request was denied.
        context: The :class:`GovernanceContext` at the time of denial.
    """

    policy_name: str
    reason: str
    context: GovernanceContext


__all__ = [
    "GovernanceContext",
    "Policy",
    "PolicyDecision",
    "PolicyEffect",
    "PolicyRule",
    "PolicyScope",
    "PolicyViolation",
]
