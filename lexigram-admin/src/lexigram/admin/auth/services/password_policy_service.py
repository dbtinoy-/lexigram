"""Admin password policy validation service."""

from __future__ import annotations

from lexigram.admin.auth.protocols import AdminPasswordPolicyServiceProtocol
from lexigram.admin.auth.types import (
    AdminPasswordRule,
    AdminPasswordValidationResult,
    AdminPasswordViolation,
)
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)

# Top 500 most common passwords (abbreviated for embedded list).
# A full production deployment should embed the NIST top-10 000 list.
_COMMON_PASSWORDS: frozenset[str] = frozenset(
    {
        "password",
        "password1",
        "password123",
        "123456",
        "123456789",
        "12345678",
        "1234567890",
        "qwerty",
        "qwerty123",
        "abc123",
        "letmein",
        "monkey",
        "dragon",
        "master",
        "sunshine",
        "princess",
        "welcome",
        "shadow",
        "superman",
        "michael",
        "football",
        "baseball",
        "iloveyou",
        "trustno1",
        "hunter2",
        "admin",
        "admin123",
        "administrator",
        "root",
        "toor",
        "passw0rd",
        "p@ssword",
        "p@ssw0rd",
        "pass@word",
        "test",
        "test123",
        "demo",
        "demo123",
        "guest",
        "guest123",
        "login",
        "login123",
        "changeme",
        "change_me",
        "default",
        "secret",
        "secret123",
        "temp",
        "temp123",
        "temporary",
        "letmein1",
        "letmein123",
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
        "1q2w3e4r",
        "1q2w3e",
        "11111111",
        "22222222",
        "33333333",
        "00000000",
        "111111111",
        "password2",
        "Password1",
        "Password1!",
        "P@ssword1",
        "Admin@123",
        "Welcome1",
        "Welcome@1",
        "Hello123",
        "Summer2023",
        "Winter2023",
        "Spring2023",
        "Autumn2023",
        "January1",
        "February1",
        "March2023",
    }
)

# Characters that satisfy the "special" requirement.
_SPECIAL_CHARS: frozenset[str] = frozenset(r"""!@#$%^&*()_+-=[]{}|;':",./<>?`~\\""")


@inject
class AdminPasswordPolicyService:
    """Password policy validation service for admin accounts.

    Validates passwords against configurable rules following NIST SP 800-63B
    guidelines. Returns ALL violations in a single call, not just the first.
    """

    def __init__(
        self,
        min_length: int = 12,
        max_length: int = 128,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
        reject_common_passwords: bool = True,
        reject_containing_email: bool = True,
    ) -> None:
        """Initialize with policy configuration.

        Args:
            min_length: Minimum password length (default 12).
            max_length: Maximum password length (default 128).
            require_uppercase: Require at least one uppercase letter.
            require_lowercase: Require at least one lowercase letter.
            require_digit: Require at least one digit.
            require_special: Require at least one special character.
            reject_common_passwords: Reject passwords in the common list.
            reject_containing_email: Reject passwords that contain the email.
        """
        self._min_length = min_length
        self._max_length = max_length
        self._require_uppercase = require_uppercase
        self._require_lowercase = require_lowercase
        self._require_digit = require_digit
        self._require_special = require_special
        self._reject_common = reject_common_passwords
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

        Checks ALL rules and returns every violation, not just the first one.

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

        # --- Length ---
        if len(password) < self._min_length:
            violations.append(
                AdminPasswordViolation(
                    rule=AdminPasswordRule.TOO_SHORT,
                    message=(
                        f"Password must be at least {self._min_length} characters."
                    ),
                )
            )

        if len(password) > self._max_length:
            violations.append(
                AdminPasswordViolation(
                    rule=AdminPasswordRule.TOO_LONG,
                    message=(
                        f"Password must not exceed {self._max_length} characters."
                    ),
                )
            )

        # --- Character class requirements ---
        if self._require_uppercase and not any(c.isupper() for c in password):
            violations.append(
                AdminPasswordViolation(
                    rule=AdminPasswordRule.MISSING_UPPERCASE,
                    message="Password must contain at least one uppercase letter.",
                )
            )

        if self._require_lowercase and not any(c.islower() for c in password):
            violations.append(
                AdminPasswordViolation(
                    rule=AdminPasswordRule.MISSING_LOWERCASE,
                    message="Password must contain at least one lowercase letter.",
                )
            )

        if self._require_digit and not any(c.isdigit() for c in password):
            violations.append(
                AdminPasswordViolation(
                    rule=AdminPasswordRule.MISSING_DIGIT,
                    message="Password must contain at least one digit.",
                )
            )

        if self._require_special and not any(c in _SPECIAL_CHARS for c in password):
            violations.append(
                AdminPasswordViolation(
                    rule=AdminPasswordRule.MISSING_SPECIAL,
                    message=(
                        "Password must contain at least one special character"
                        " (!@#$%^&* etc.)."
                    ),
                )
            )

        # --- Common-password check ---
        if self._reject_common and password.lower() in _COMMON_PASSWORDS:
            violations.append(
                AdminPasswordViolation(
                    rule=AdminPasswordRule.COMMON_PASSWORD,
                    message=(
                        "Password is too common. Please choose a more unique password."
                    ),
                )
            )

        # --- Email-containment check ---
        if self._reject_email and email:
            email_lower = email.lower()
            local_part = (
                email_lower.split("@")[0] if "@" in email_lower else email_lower
            )
            if len(local_part) >= 4 and local_part in password.lower():
                violations.append(
                    AdminPasswordViolation(
                        rule=AdminPasswordRule.CONTAINS_EMAIL,
                        message="Password must not contain your email address.",
                    )
                )

        logger.debug(
            "password_policy.validated",
            violation_count=len(violations),
            is_valid=len(violations) == 0,
        )

        return AdminPasswordValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
        )


# Verify that the concrete class satisfies the protocol at import time.
_: AdminPasswordPolicyServiceProtocol = AdminPasswordPolicyService.__new__(
    AdminPasswordPolicyService
)

__all__ = ["AdminPasswordPolicyService"]
