"""Static catalog wiring every Lexigram architectural rule."""

from __future__ import annotations

from dev.core.rules_catalog.security_rules import (
    _detect_cors_wildcard_credentials,
    _detect_hardcoded_secret,
    _detect_jwt_verification_disabled,
    _detect_tls_verify_disabled,
)
from dev.core.rules_catalog.structure_rules import (
    _detect_cross_extension_imports,
    _detect_init_no_logic,
    _detect_pseudo_enum,
    _detect_relative_imports,
)
from dev.core.rules_catalog.types import RuleDefinition, RuleSeverity


def build_rules_catalog() -> tuple[RuleDefinition, ...]:
    """Return the static catalog of Lexigram architectural rules."""

    return (
        RuleDefinition(
            rule_id="init-no-logic",
            severity=RuleSeverity.IMPORTANT,
            owner="framework",
            rationale="__init__.py files should contain exports only so package entry points stay declarative.",
            detector=_detect_init_no_logic,
        ),
        RuleDefinition(
            rule_id="import-absolute-only",
            severity=RuleSeverity.IMPORTANT,
            owner="framework",
            rationale="Relative imports obscure package boundaries and are disallowed across the framework.",
            detector=_detect_relative_imports,
        ),
        RuleDefinition(
            rule_id="no-cross-extension-import",
            severity=RuleSeverity.CRITICAL,
            owner="architecture",
            rationale="Core and extension packages must respect the declared dependency hierarchy instead of importing across forbidden boundaries.",
            detector=_detect_cross_extension_imports,
        ),
        RuleDefinition(
            rule_id="enum-must-use-enum",
            severity=RuleSeverity.MINOR,
            owner="framework",
            rationale="Enumeration-like classes must inherit from enum.Enum for type safety and consistency.",
            detector=_detect_pseudo_enum,
        ),
        RuleDefinition(
            rule_id="sec-tls-verify-disabled",
            severity=RuleSeverity.IMPORTANT,
            owner="security",
            rationale="TLS certificate verification must stay enabled for every outbound client; verify=False or an unverified context defeats transport encryption.",
            detector=_detect_tls_verify_disabled,
        ),
        RuleDefinition(
            rule_id="sec-hardcoded-secret",
            severity=RuleSeverity.IMPORTANT,
            owner="security",
            rationale="Long literal secrets assigned to secret-named variables must come from configuration, not source code.",
            detector=_detect_hardcoded_secret,
        ),
        RuleDefinition(
            rule_id="sec-cors-wildcard-credentials",
            severity=RuleSeverity.IMPORTANT,
            owner="security",
            rationale="A wildcard CORS origin combined with allow_credentials exposes authenticated endpoints to any origin.",
            detector=_detect_cors_wildcard_credentials,
        ),
        RuleDefinition(
            rule_id="sec-jwt-verification-disabled",
            severity=RuleSeverity.CRITICAL,
            owner="security",
            rationale="Signing JWT verification must never be disabled or pinned to the 'none' algorithm.",
            detector=_detect_jwt_verification_disabled,
        ),
    )
