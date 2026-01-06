"""Extended tests for admin validation rules and validator factories.

Covers:
- IsValidAdminEmail
- StrongPassword
- IsValidUsername
- create_user_validator / update_user_validator factories
- validation __init__ re-exports
"""

from __future__ import annotations

import pytest

from lexigram.admin.validation import (
    IsValidAdminEmail,
    IsValidUsername,
    StrongPassword,
    create_user_validator,
    update_user_validator,
)
from lexigram.admin.validation.rules import (
    IsValidAdminEmail as IsValidAdminEmailDirect,
    IsValidUsername as IsValidUsernameDirect,
    StrongPassword as StrongPasswordDirect,
)


# ---------------------------------------------------------------------------
# IsValidAdminEmail
# ---------------------------------------------------------------------------


class TestIsValidAdminEmail:
    """Tests for IsValidAdminEmail rule."""

    def setup_method(self) -> None:
        self.rule = IsValidAdminEmail()

    def test_valid_email_returns_ok(self) -> None:
        result = self.rule("admin@example.com", "email")
        assert result.is_ok()
        assert result.unwrap() == "admin@example.com"

    def test_valid_email_with_subdomain(self) -> None:
        result = self.rule("user@mail.example.co.uk", "email")
        assert result.is_ok()

    def test_valid_email_with_plus(self) -> None:
        result = self.rule("user+tag@example.org", "email")
        assert result.is_ok()

    def test_invalid_email_no_at(self) -> None:
        result = self.rule("notanemail", "email")
        assert result.is_err()
        err = result.unwrap_err()
        assert err.field == "email"
        assert err.code == "invalid_admin_email"

    def test_invalid_email_missing_domain(self) -> None:
        result = self.rule("user@", "email")
        assert result.is_err()

    def test_invalid_email_no_tld(self) -> None:
        result = self.rule("user@domain", "email")
        assert result.is_err()

    def test_none_value_returns_ok(self) -> None:
        # None is allowed (use `required()` separately to enforce presence)
        result = self.rule(None, "email")
        assert result.is_ok()

    def test_re_export_matches_direct_import(self) -> None:
        assert IsValidAdminEmail is IsValidAdminEmailDirect


# ---------------------------------------------------------------------------
# StrongPassword
# ---------------------------------------------------------------------------


class TestStrongPassword:
    """Tests for StrongPassword rule."""

    def setup_method(self) -> None:
        self.rule = StrongPassword()

    def test_valid_strong_password(self) -> None:
        result = self.rule("Str0ng!Pass", "password")
        assert result.is_ok()
        assert result.unwrap() == "Str0ng!Pass"

    def test_valid_complex_password(self) -> None:
        result = self.rule("MyP@ssw0rd#2024", "password")
        assert result.is_ok()

    def test_password_too_short(self) -> None:
        result = self.rule("Ab1!", "password")
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "password_too_short"

    def test_password_no_uppercase(self) -> None:
        result = self.rule("lowercase1!", "password")
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "password_no_uppercase"

    def test_password_no_lowercase(self) -> None:
        result = self.rule("UPPERCASE1!", "password")
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "password_no_lowercase"

    def test_password_no_digit(self) -> None:
        result = self.rule("NoDigits!", "password")
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "password_no_digit"

    def test_password_no_special_char(self) -> None:
        result = self.rule("NoSpecial1", "password")
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "password_no_special"

    def test_none_value_returns_ok(self) -> None:
        result = self.rule(None, "password")
        assert result.is_ok()

    def test_exactly_eight_chars(self) -> None:
        result = self.rule("Abc!1234", "password")
        assert result.is_ok()

    def test_field_name_in_error_message(self) -> None:
        result = self.rule("short", "new_password")
        assert result.is_err()
        err = result.unwrap_err()
        assert err.field == "new_password"
        assert "new_password" in err.message

    def test_re_export_matches_direct_import(self) -> None:
        assert StrongPassword is StrongPasswordDirect


# ---------------------------------------------------------------------------
# IsValidUsername
# ---------------------------------------------------------------------------


class TestIsValidUsername:
    """Tests for IsValidUsername rule."""

    def setup_method(self) -> None:
        self.rule = IsValidUsername()

    def test_valid_username_alphanumeric(self) -> None:
        result = self.rule("admin123", "username")
        assert result.is_ok()

    def test_valid_username_with_underscore(self) -> None:
        result = self.rule("admin_user", "username")
        assert result.is_ok()

    def test_valid_username_min_length(self) -> None:
        result = self.rule("abc", "username")
        assert result.is_ok()

    def test_valid_username_max_length(self) -> None:
        result = self.rule("a" * 64, "username")
        assert result.is_ok()

    def test_invalid_username_too_short(self) -> None:
        result = self.rule("ab", "username")
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "invalid_username"
        assert err.field == "username"

    def test_invalid_username_too_long(self) -> None:
        result = self.rule("a" * 65, "username")
        assert result.is_err()

    def test_invalid_username_with_hyphen(self) -> None:
        result = self.rule("admin-user", "username")
        assert result.is_err()

    def test_invalid_username_with_space(self) -> None:
        result = self.rule("admin user", "username")
        assert result.is_err()

    def test_invalid_username_with_dot(self) -> None:
        result = self.rule("admin.user", "username")
        assert result.is_err()

    def test_none_value_returns_ok(self) -> None:
        result = self.rule(None, "username")
        assert result.is_ok()

    def test_re_export_matches_direct_import(self) -> None:
        assert IsValidUsername is IsValidUsernameDirect


# ---------------------------------------------------------------------------
# Validator factories
# ---------------------------------------------------------------------------


class TestCreateUserValidator:
    """Tests for create_user_validator factory."""

    def test_returns_validator_instance(self) -> None:
        from lexigram.validation.engine import ValidatorImpl as Validator

        v = create_user_validator()
        assert isinstance(v, Validator)

    def test_valid_user_data_passes(self) -> None:
        v = create_user_validator()
        result = v.validate(
            {
                "email": "admin@example.com",
                "password": "Str0ng!Pass",
                "username": "admin_user",
            }
        )
        assert result.is_ok()

    def test_missing_email_fails(self) -> None:
        v = create_user_validator()
        result = v.validate(
            {
                "password": "Str0ng!Pass",
                "username": "admin_user",
            }
        )
        assert result.is_err()

    def test_invalid_email_fails(self) -> None:
        v = create_user_validator()
        result = v.validate(
            {
                "email": "notanemail",
                "password": "Str0ng!Pass",
                "username": "admin_user",
            }
        )
        assert result.is_err()

    def test_weak_password_fails(self) -> None:
        v = create_user_validator()
        result = v.validate(
            {
                "email": "admin@example.com",
                "password": "weak",
                "username": "admin_user",
            }
        )
        assert result.is_err()


class TestUpdateUserValidator:
    """Tests for update_user_validator factory."""

    def test_returns_validator_instance(self) -> None:
        from lexigram.validation.engine import ValidatorImpl as Validator

        v = update_user_validator()
        assert isinstance(v, Validator)

    def test_valid_update_data_passes(self) -> None:
        v = update_user_validator()
        result = v.validate(
            {
                "email": "new@example.com",
                "username": "new_user",
            }
        )
        assert result.is_ok()

    def test_empty_data_passes_update(self) -> None:
        # Update validator doesn't require fields
        v = update_user_validator()
        result = v.validate({})
        assert result.is_ok()

    def test_invalid_email_fails_update(self) -> None:
        v = update_user_validator()
        result = v.validate({"email": "bademail"})
        assert result.is_err()

    def test_invalid_username_fails_update(self) -> None:
        v = update_user_validator()
        result = v.validate({"username": "a"})
        assert result.is_err()
