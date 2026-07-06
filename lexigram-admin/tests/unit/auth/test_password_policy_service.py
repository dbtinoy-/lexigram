"""Unit tests for AdminPasswordPolicyService (lexigram-auth delegation)."""

from __future__ import annotations

import pytest

from lexigram.admin.auth.services.password_policy_service import (
    AdminPasswordPolicyService,
)
from lexigram.admin.auth.types import AdminPasswordRule
from lexigram.auth import PasswordPolicy


def _make_service(
    reject_containing_email: bool = True,
) -> tuple[AdminPasswordPolicyService, PasswordPolicy]:
    """Build the service over the admin-default rule set (min 12, all classes)."""
    policy = PasswordPolicy(
        min_length=12,
        max_length=128,
        require_uppercase=True,
        require_lowercase=True,
        require_digits=True,
        require_special=True,
        prevent_common=True,
    )
    return (
        AdminPasswordPolicyService(
            policy=policy, reject_containing_email=reject_containing_email
        ),
        policy,
    )


def test_parity_with_auth_policy_verdicts() -> None:
    """Verdicts are identical to the delegated lexigram-auth policy."""
    service, policy = _make_service()
    samples = ["short", "Correct-Horse-42!Battery", "password123", "welcome"]

    for sample in samples:
        assert service.is_valid(sample) is policy.is_valid(sample)

    assert service.is_valid("short") is False
    assert service.is_valid("Correct-Horse-42!Battery") is True


def test_validate_reports_all_violations() -> None:
    service, _ = _make_service()

    result = service.validate("short1")

    assert result.is_valid is False
    rules = {v.rule for v in result.violations}
    assert AdminPasswordRule.TOO_SHORT in rules
    assert AdminPasswordRule.MISSING_UPPERCASE in rules
    assert AdminPasswordRule.MISSING_SPECIAL in rules
    assert AdminPasswordRule.MISSING_DIGIT not in rules


def test_validate_strong_password_has_no_violations() -> None:
    service, _ = _make_service()

    result = service.validate("Correct-Horse-42!Battery")

    assert result.is_valid is True
    assert result.violations == []


def test_validate_rejects_common_password_listed_in_auth_policy() -> None:
    service, _ = _make_service()

    result = service.validate("Password1!")

    assert result.is_valid is False
    assert any(
        v.rule is AdminPasswordRule.COMMON_PASSWORD for v in result.violations
    )


def test_validate_email_containment_rule() -> None:
    service, _ = _make_service()

    result = service.validate("Admin@example.com42!", email="admin@example.com")

    assert result.is_valid is False
    assert any(
        v.rule is AdminPasswordRule.CONTAINS_EMAIL for v in result.violations
    )


def test_validate_email_rule_disabled() -> None:
    service, _ = _make_service(reject_containing_email=False)

    result = service.validate("Admin@example.com42!", email="admin@example.com")

    assert result.is_valid is True
    assert result.violations == []


def test_default_construction_uses_admin_rule_set() -> None:
    service = AdminPasswordPolicyService()

    assert service.is_valid("short") is False
    assert service.is_valid("Correct-Horse-42!Battery") is True