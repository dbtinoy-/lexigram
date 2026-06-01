"""Admin password policy validation service.

All rule evaluation is delegated to the single lexigram-auth
``PasswordPolicy`` implementation (NIST rule set + common-password
list); this adapter keeps the admin result contract — per-rule
``AdminPasswordViolation`` entries with UI-safe messages plus the
admin-specific email-containment rule — and maps the auth engine's
failure report onto it.
"""

from __future__ import annotations

from lexigram.admin.auth.protocols import AdminPasswordPolicyServiceProtocol
from lexigram.admin.auth.types import (
    AdminPasswordRule,
    AdminPasswordValidationResult,
    AdminPasswordViolation,
)
from lexigram.auth import PasswordPolicy
from lexigram.contracts.auth import PasswordPolicyProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


def _default_policy() -> PasswordPolicy:
    """Build the admin-default policy (min 12, all classes required)."""
    return PasswordPolicy(
        min_length=12,
        max_length=128,
        require_uppercase=True,
        require_lowercase=True,
        require_digits=True,
        require_special=True,
        prevent_common=True,
    )


@inject
class AdminPasswordPolicyService:
    """Password policy validation service for admin accounts.

    Delegates rule evaluation (length, character classes, common
    passwords) to the injected ``PasswordPolicyProtocol`` implementation
    from lexigram-auth.  Keeps the admin-only email-containment rule and
    translates the auth engine's failure report into per-rule
    ``AdminPasswordViolation`` entries.

    Args:
        policy: lexigram-auth policy implementation carrying the
            configured rule set; defaults to the admin rule set.
        reject_containing_email: Reject passwords that contain the
            admin user's email local-part.
    """

    def __init__(
        self,
        policy: PasswordPolicyProtocol | None = None,
        reject_containing_email: bool = True,
    ) -> None:
        self._policy = policy if policy is not None else _default_policy()
        self._reject_email = reject_containing_email

    # ------------------------------------------------------------------
    # AdminPasswordPolicyServiceProtocol
    # ------------------------------------------------------------------

    def validate(
        self,
        password: str,
        email: str | None = None,
    ) -> AdminPasswordValidationResult:
        """Validate a password against all configured rules.

        Delegates the shared rule evaluation to lexigram-auth's policy
        implementation and maps its failure report onto the admin
        violation contract.  The admin-specific email-containment rule
        is checked here.

        Args:
            password: Plain-text password to validate.
            email: Optional email — if provided and reject_containing_email
                is True, checks whether the password contains the email
                local-part.

        Returns:
            AdminPasswordValidationResult with is_valid and the full
            violations list.
        """
        violations: list[AdminPasswordViolation] = []
        try:
            self._policy.validate(password)
        except ValueError as exc:
            violations = self._map_failures(str(exc), password)

        if self._reject_email and email:
            violation = self._email_violation(password, email)
            if violation is not None:
                violations.append(violation)

        logger.debug(
            "password_policy.validated",
            violation_count=len(violations),
            is_valid=len(violations) == 0,
        )

        return AdminPasswordValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
        )

    def is_valid(self, password: str) -> bool:
        """Return True when the password satisfies the delegated policy."""
        return self._policy.is_valid(password)

    # ------------------------------------------------------------------
    # Failure-report mapping
    # ------------------------------------------------------------------

    _RULE_MAP: tuple[tuple[str, AdminPasswordRule], ...] = (
        ("uppercase", AdminPasswordRule.MISSING_UPPERCASE),
        ("lowercase", AdminPasswordRule.MISSING_LOWERCASE),
        ("digit", AdminPasswordRule.MISSING_DIGIT),
        ("special character", AdminPasswordRule.MISSING_SPECIAL),
        ("too common", AdminPasswordRule.COMMON_PASSWORD),
        ("at most", AdminPasswordRule.TOO_LONG),
        ("at least", AdminPasswordRule.TOO_SHORT),
    )

    def _map_failures(self, report: str, password: str) -> list[AdminPasswordViolation]:
        violations: list[AdminPasswordViolation] = []
        for part in report.split("; "):
            rule = next(
                (rule for needle, rule in self._RULE_MAP if needle in part),
                None,
            )
            if rule is None:
                logger.warning("password_policy.unmapped_rule", rule_text=part)
                continue
            violations.append(
                AdminPasswordViolation(
                    rule=rule, message=self._message_for(rule, password)
                )
            )
        return violations

    def _message_for(self, rule: AdminPasswordRule, password: str) -> str:
        """Return the stable admin UI message for a violated rule."""
        if rule is AdminPasswordRule.TOO_SHORT:
            minimum = int(getattr(self._policy, "min_length", 12))
            return f"Password must be at least {minimum} characters."
        if rule is AdminPasswordRule.TOO_LONG:
            maximum = int(getattr(self._policy, "max_length", 128))
            return f"Password must not exceed {maximum} characters."
        if rule is AdminPasswordRule.MISSING_UPPERCASE:
            return "Password must contain at least one uppercase letter."
        if rule is AdminPasswordRule.MISSING_LOWERCASE:
            return "Password must contain at least one lowercase letter."
        if rule is AdminPasswordRule.MISSING_DIGIT:
            return "Password must contain at least one digit."
        if rule is AdminPasswordRule.MISSING_SPECIAL:
            return (
                "Password must contain at least one special character (!@#$%^&* etc.)."
            )
        return "Password is too common. Please choose a more unique password."

    def _email_violation(
        self, password: str, email: str | None
    ) -> AdminPasswordViolation | None:
        """Return a CONTAINS_EMAIL violation when the password embeds the email."""
        if not email:
            return None
        email_lower = email.lower()
        local_part = email_lower.split("@")[0] if "@" in email_lower else email_lower
        if len(local_part) >= 4 and local_part in password.lower():
            return AdminPasswordViolation(
                rule=AdminPasswordRule.CONTAINS_EMAIL,
                message="Password must not contain your email address.",
            )
        return None


# Verify that the concrete class satisfies the protocol at import time.
_: AdminPasswordPolicyServiceProtocol = AdminPasswordPolicyService.__new__(
    AdminPasswordPolicyService
)

__all__ = ["AdminPasswordPolicyService"]
