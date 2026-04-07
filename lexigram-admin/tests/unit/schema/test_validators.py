from __future__ import annotations

import pytest

from lexigram.admin.schema.exceptions import FieldError
from lexigram.admin.schema.validators import (
    EmailValidator,
    FieldValidator,
    LengthValidator,
    PatternValidator,
    RangeValidator,
    RequiredValidator,
    URLValidator,
)


class TestRequiredValidator:
    """RequiredValidator rejects None, empty, whitespace; passes non-empty."""

    def test_rejects_none(self) -> None:
        validator = RequiredValidator()
        result = validator(None)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_rejects_empty_string(self) -> None:
        validator = RequiredValidator()
        result = validator("")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_rejects_whitespace_only(self) -> None:
        validator = RequiredValidator()
        result = validator("   ")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_passes_non_empty_string(self) -> None:
        validator = RequiredValidator()
        result = validator("hello")
        assert result.is_ok()
        assert result.unwrap() == "hello"

    def test_passes_non_string_value(self) -> None:
        validator = RequiredValidator()
        result = validator(0)
        assert result.is_ok()
        assert result.unwrap() == 0


class TestLengthValidator:
    """LengthValidator rejects too-short and too-long values."""

    def test_rejects_too_short(self) -> None:
        validator = LengthValidator(min_length=3, max_length=10)
        result = validator("ab")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_rejects_too_long(self) -> None:
        validator = LengthValidator(min_length=3, max_length=10)
        result = validator("abcdefghijk")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_passes_within_range(self) -> None:
        validator = LengthValidator(min_length=3, max_length=10)
        result = validator("hello")
        assert result.is_ok()
        assert result.unwrap() == "hello"

    def test_passes_at_min_boundary(self) -> None:
        validator = LengthValidator(min_length=3, max_length=10)
        result = validator("abc")
        assert result.is_ok()
        assert result.unwrap() == "abc"

    def test_passes_at_max_boundary(self) -> None:
        validator = LengthValidator(min_length=3, max_length=10)
        result = validator("abcdefghij")
        assert result.is_ok()
        assert result.unwrap() == "abcdefghij"


class TestRangeValidator:
    """RangeValidator rejects out-of-bound numeric values."""

    def test_rejects_below_min(self) -> None:
        validator = RangeValidator(min_value=0, max_value=100)
        result = validator(-1)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_rejects_above_max(self) -> None:
        validator = RangeValidator(min_value=0, max_value=100)
        result = validator(101)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_passes_within_range(self) -> None:
        validator = RangeValidator(min_value=0, max_value=100)
        result = validator(50)
        assert result.is_ok()
        assert result.unwrap() == 50

    def test_passes_at_min_boundary(self) -> None:
        validator = RangeValidator(min_value=0, max_value=100)
        result = validator(0)
        assert result.is_ok()
        assert result.unwrap() == 0

    def test_passes_at_max_boundary(self) -> None:
        validator = RangeValidator(min_value=0, max_value=100)
        result = validator(100)
        assert result.is_ok()
        assert result.unwrap() == 100

    def test_rejects_non_numeric(self) -> None:
        validator = RangeValidator(min_value=0, max_value=100)
        result = validator("abc")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)


class TestEmailValidator:
    """EmailValidator rejects non-email strings."""

    def test_rejects_no_at_sign(self) -> None:
        validator = EmailValidator()
        result = validator("not-an-email")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_rejects_no_domain(self) -> None:
        validator = EmailValidator()
        result = validator("user@")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_rejects_no_local_part(self) -> None:
        validator = EmailValidator()
        result = validator("@domain.com")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_rejects_no_dot_in_domain(self) -> None:
        validator = EmailValidator()
        result = validator("user@domain")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_passes_simple_email(self) -> None:
        validator = EmailValidator()
        result = validator("user@example.com")
        assert result.is_ok()
        assert result.unwrap() == "user@example.com"

    def test_passes_email_with_plus_tag(self) -> None:
        validator = EmailValidator()
        result = validator("user.name+tag@example.co.uk")
        assert result.is_ok()
        assert result.unwrap() == "user.name+tag@example.co.uk"


class TestURLValidator:
    """URLValidator rejects non-URL strings."""

    def test_rejects_random_string(self) -> None:
        validator = URLValidator()
        result = validator("not-a-url")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_rejects_wrong_scheme(self) -> None:
        validator = URLValidator()
        result = validator("ftp://example.com")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_passes_https(self) -> None:
        validator = URLValidator()
        result = validator("https://example.com")
        assert result.is_ok()
        assert result.unwrap() == "https://example.com"

    def test_passes_http_with_path(self) -> None:
        validator = URLValidator()
        result = validator("http://example.com/path?query=1")
        assert result.is_ok()
        assert result.unwrap() == "http://example.com/path?query=1"

    def test_rejects_bare_scheme(self) -> None:
        validator = URLValidator()
        result = validator("http://")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)


class TestPatternValidator:
    """PatternValidator rejects strings not matching the regex."""

    def test_rejects_non_matching(self) -> None:
        validator = PatternValidator(r"^\d{3}-\d{4}$")
        result = validator("abc")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_rejects_partial_match(self) -> None:
        validator = PatternValidator(r"^\d{3}-\d{4}$")
        result = validator("12345")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_passes_matching(self) -> None:
        validator = PatternValidator(r"^\d{3}-\d{4}$")
        result = validator("123-4567")
        assert result.is_ok()
        assert result.unwrap() == "123-4567"


class TestValidatorChaining:
    """Multiple validators can be composed in sequence."""

    def test_chaining_required_then_length_passes(self) -> None:
        validators: list[FieldValidator] = [
            RequiredValidator(),
            LengthValidator(min_length=3, max_length=10),
        ]
        value: str = "hello"
        for v in validators:
            result = v(value)
            assert result.is_ok(), f"Failed at {v.__class__.__name__}"
        assert value == "hello"

    def test_chaining_required_then_length_fails_required(self) -> None:
        validators: list[FieldValidator] = [
            RequiredValidator(),
            LengthValidator(min_length=3, max_length=10),
        ]
        result = validators[0](None)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_chaining_required_then_length_fails_length(self) -> None:
        validators: list[FieldValidator] = [
            RequiredValidator(),
            LengthValidator(min_length=3, max_length=10),
        ]
        result = validators[1]("ab")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FieldError)

    def test_protocol_conformance(self) -> None:
        """All validator classes satisfy the FieldValidator protocol."""
        validators: list[FieldValidator] = [
            RequiredValidator(),
            LengthValidator(min_length=1, max_length=5),
            RangeValidator(min_value=0, max_value=10),
            EmailValidator(),
            URLValidator(),
            PatternValidator(r".*"),
        ]
        for v in validators:
            assert isinstance(v, FieldValidator)
