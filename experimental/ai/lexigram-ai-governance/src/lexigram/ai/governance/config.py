"""Configuration for AI Governance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, cast

from lexigram.ai.governance import constants as const
from lexigram.config import (
    BaseConfig,
)
from lexigram.contracts.core.config import ConfigIssue, Environment
from lexigram.validation import ConfigDict, Field



@dataclass(init=False)
class GovernanceConfig(BaseConfig):
    """Configuration for AI Governance.

    Loaded from the ``ai_governance:`` key in application.yaml, with environment
    variable overrides via ``LEX_AI_GOVERNANCE__*`` prefix.
    """

    config_section: ClassVar[str] = "ai_governance"

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": const.ENV_PREFIX,
            "env_nested_delimiter": const.ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    enabled: bool = Field(default=True, description="Enable AI governance")
    monthly_budget: float | None = Field(
        default=None,
        description="Monthly budget in dollars",
    )
    max_tokens_per_request: int | None = Field(
        default=None,
        description="Max tokens per request",
    )
    rpm_limit: int | None = Field(default=None, description="Requests Per Minute limit")
    tpm_limit: int | None = Field(default=None, description="Tokens Per Minute limit")
    restricted_models: list[str] = Field(
        default_factory=list,
        description="List of restricted models",
    )
    enforce_budget: bool = Field(default=True, description="Enforce budget limits")
    soft_limit_pct: float | None = Field(
        default=None,
        description=(
            "Fraction of monthly_budget at which to emit a soft-limit warning "
            "(e.g. 0.8 = warn at 80%). No hard block is applied at this threshold."
        ),
        ge=0.0,
        le=1.0,
    )
    max_request_cost: float | None = Field(
        default=None,
        description=(
            "Maximum cost in dollars for a single request. "
            "Requests with an estimated cost above this threshold are rejected "
            "before they reach the monthly-budget check."
        ),
        ge=0.0,
    )
    model_allowlist: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Per-user/role model allowlist. Keys are user IDs or role names; "
            "values are lists of allowed model patterns (supports glob syntax, "
            "e.g. 'gpt-4*', 'claude-3-*')."
        ),
    )
    model_denylist: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Per-user/role model denylist. Keys are user IDs or role names; "
            "values are lists of denied model patterns (supports glob syntax). "
            "Denylist is checked after allowlist."
        ),
    )
    resource_units: list = Field(
        default_factory=list,
        description=(
            "Resource units this governance instance tracks. "
            "Per-tenant limits are configured via TenantConfigService overrides."
        ),
    )
    fail_open_on_persistence_error: bool = Field(
        default=False,
        description=(
            "Allow requests when the persistence backend is unavailable. "
            "When False (default, fail-closed), a persistence failure (e.g. Redis "
            "down) denies the request: the budget check treats spend as unknown "
            "and denies, the RPM check denies, and cost recording is skipped; "
            "every failure is logged. When True (fail-open), the same failure "
            "allows the request and skips cost recording, trading spend/rate "
            "enforcement for availability during infrastructure outages."
        ),
    )

    def validate_for_environment(
        self, env: Environment | None = None
    ) -> list[ConfigIssue]:
        """Check config is safe for the target environment."""
        issues: list[ConfigIssue] = []

        if env == Environment.PRODUCTION:
            if not self.enforce_budget:
                issues.append(
                    ConfigIssue(
                        severity="warning",
                        field="enforce_budget",
                        message="Budget enforcement disabled in production",
                        suggestion=(
                            f"Set {const.ENV_PREFIX}ENFORCE_BUDGET=true or remove "
                            "the override to enforce budget limits."
                        ),
                    )
                )
            if self.monthly_budget is None:
                issues.append(
                    ConfigIssue(
                        severity="warning",
                        field="monthly_budget",
                        message="No monthly budget configured in production",
                        suggestion=(
                            f"Set {const.ENV_PREFIX}MONTHLY_BUDGET to a dollar amount "
                            "to prevent runaway costs."
                        ),
                    )
                )

        return issues


__all__ = ["GovernanceConfig"]
