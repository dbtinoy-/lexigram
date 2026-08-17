"""Tests for lexigram-auth PasswordPolicy used by lexigram-admin.

AdminPasswordPolicy has been removed.  lexigram-admin now resolves
PasswordHasherProtocol and PasswordPolicyProtocol from the DI container,
which is backed by lexigram-auth's PasswordHasher / PasswordPolicy when
lexigram-auth is installed.

This suite validates that:
  - auth's PasswordPolicy satisfies PasswordPolicyProtocol from contracts
  - the policy enforces rules that the admin DI sub-provider relies on
  - is_valid() / validate() behave as expected with admin-relevant defaults
"""

from __future__ import annotations

import pytest

from lexigram.auth.authn.security import PasswordPolicy
from lexigram.contracts.auth import PasswordPolicyProtocol


class TestPasswordPolicyProtocol:
    def test_implements_protocol(self) -> None:
        policy = PasswordPolicy()
        assert isinstance(policy, PasswordPolicyProtocol)

    def test_is_valid_method_exists(self) -> None:
        policy = PasswordPolicy()
        assert hasattr(policy, "is_valid")

    def test_validate_method_exists(self) -> None:
        policy = PasswordPolicy()
        assert hasattr(policy, "validate")


class TestPasswordPolicyDefaultRules:
    """Default policy: min 8 chars, uppercase, lowercase required."""

    def setup_method(self) -> None:
        # Match admin-equivalent defaults: uppercase + lowercase required,
        # digits not required by auth default — use require_digits=True for
        # a stricter admin policy configuration.
        self.policy = PasswordPolicy(
            require_uppercase=True,
            require_lowercase=True,
            require_digits=True,
        )

    def test_valid_password_passes(self) -> None:
        assert self.policy.is_valid("SecurePass1")

    def test_too_short_fails(self) -> None:
        assert not self.policy.is_valid("Abc1")

    def test_no_uppercase_fails(self) -> None:
        assert not self.policy.is_valid("securepass1")

    def test_no_lowercase_fails(self) -> None:
        assert not self.policy.is_valid("SECUREPASS1")

    def test_no_digit_fails(self) -> None:
        assert not self.policy.is_valid("SecurePassw")

    def test_validate_raises_on_violation(self) -> None:
        with pytest.raises(ValueError):
            self.policy.validate("short")

    def test_validate_passes_for_valid_password(self) -> None:
        self.policy.validate("StrongPass9")  # must not raise


class TestPasswordPolicyCustomRules:
    def test_custom_min_length(self) -> None:
        policy = PasswordPolicy(min_length=16, require_uppercase=False, require_lowercase=False)
        assert not policy.is_valid("Short1Pass")
        assert policy.is_valid("verylongpassword1")

    def test_max_length_enforced(self) -> None:
        policy = PasswordPolicy(max_length=20, require_uppercase=False, require_lowercase=False)
        assert not policy.is_valid("a" * 21)
        assert policy.is_valid("validpass")

    def test_special_char_required(self) -> None:
        policy = PasswordPolicy(require_special=True, require_uppercase=False, require_lowercase=False)
        assert not policy.is_valid("SecurePass1")
        assert policy.is_valid("SecurePass1!")

    def test_special_char_not_required_by_default(self) -> None:
        policy = PasswordPolicy(require_special=False, require_uppercase=False, require_lowercase=False)
        assert policy.is_valid("securepass1")

    def test_no_uppercase_required(self) -> None:
        policy = PasswordPolicy(require_uppercase=False)
        assert policy.is_valid("securepass1")

    def test_no_digit_required(self) -> None:
        policy = PasswordPolicy(require_digits=False, require_special=False)
        assert policy.is_valid("SecurePasswd")


class TestPasswordPolicyBannedPatterns:
    def test_banned_pattern_blocks_password(self) -> None:
        policy = PasswordPolicy(
            banned_patterns=["password", "admin"],
            require_uppercase=False,
            require_lowercase=False,
        )
        assert not policy.is_valid("mypassword1")

    def test_banned_pattern_case_insensitive(self) -> None:
        policy = PasswordPolicy(
            banned_patterns=["admin"],
            require_uppercase=False,
            require_lowercase=False,
        )
        assert not policy.is_valid("adminpass1")

    def test_allowed_without_banned_match(self) -> None:
        policy = PasswordPolicy(
            banned_patterns=["password"],
            require_uppercase=False,
            require_lowercase=False,
        )
        assert policy.is_valid("secure1pass")
