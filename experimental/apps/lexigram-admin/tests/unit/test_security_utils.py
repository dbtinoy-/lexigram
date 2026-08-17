"""Tests for utils/security.py — mask_sensitive_data and mask_string_secrets."""

from __future__ import annotations

import pytest

from lexigram.admin.lib.security import (
    SENSITIVE_KEYS,
    mask_sensitive_data,
    mask_string_secrets,
)


class TestSensitiveKeys:
    """Tests for SENSITIVE_KEYS constant."""

    def test_is_frozenset(self) -> None:
        assert isinstance(SENSITIVE_KEYS, frozenset)

    def test_contains_password(self) -> None:
        assert "password" in SENSITIVE_KEYS

    def test_contains_token(self) -> None:
        assert "token" in SENSITIVE_KEYS

    def test_contains_secret(self) -> None:
        assert "secret" in SENSITIVE_KEYS


class TestMaskSensitiveData:
    """Tests for mask_sensitive_data."""

    def test_masks_password_key(self) -> None:
        data = {"username": "alice", "password": "secret123"}
        result = mask_sensitive_data(data)
        assert result["username"] == "alice"
        assert result["password"] == "****"

    def test_masks_token_key(self) -> None:
        data = {"access_token": "tok_xyz"}
        result = mask_sensitive_data(data)
        assert result["access_token"] == "****"

    def test_non_sensitive_keys_pass_through(self) -> None:
        data = {"name": "Alice", "age": 30, "email": "a@b.com"}
        result = mask_sensitive_data(data)
        assert result["name"] == "Alice"
        assert result["age"] == 30

    def test_custom_mask_string(self) -> None:
        data = {"password": "secret"}
        result = mask_sensitive_data(data, mask="[REDACTED]")
        assert result["password"] == "[REDACTED]"

    def test_nested_dict(self) -> None:
        data = {"user": {"name": "Alice", "password": "pwd123"}}
        result = mask_sensitive_data(data)
        assert result["user"]["name"] == "Alice"
        assert result["user"]["password"] == "****"

    def test_list_items_processed(self) -> None:
        data = [{"password": "x"}, {"name": "Alice"}]
        result = mask_sensitive_data(data)
        assert result[0]["password"] == "****"
        assert result[1]["name"] == "Alice"

    def test_tuple_items_processed(self) -> None:
        data = ({"secret": "x"}, "safe_string")
        result = mask_sensitive_data(data)
        assert isinstance(result, tuple)
        assert result[0]["secret"] == "****"
        assert result[1] == "safe_string"

    def test_primitive_returned_as_is(self) -> None:
        assert mask_sensitive_data("hello") == "hello"
        assert mask_sensitive_data(42) == 42
        assert mask_sensitive_data(None) is None
        assert mask_sensitive_data(True) is True

    def test_empty_dict(self) -> None:
        assert mask_sensitive_data({}) == {}

    def test_empty_list(self) -> None:
        assert mask_sensitive_data([]) == []

    def test_case_insensitive_key_matching(self) -> None:
        data = {"PASSWORD": "x", "Password": "y", "API_KEY": "z"}
        result = mask_sensitive_data(data)
        assert result["PASSWORD"] == "****"
        assert result["Password"] == "****"
        assert result["API_KEY"] == "****"

    def test_custom_sensitive_keys(self) -> None:
        data = {"my_secret_field": "value", "name": "Alice"}
        result = mask_sensitive_data(
            data, sensitive_keys=frozenset({"my_secret_field"})
        )
        assert result["my_secret_field"] == "****"
        assert result["name"] == "Alice"

    def test_api_key_masked(self) -> None:
        data = {"apikey": "ak_live_123"}
        result = mask_sensitive_data(data)
        assert result["apikey"] == "****"

    def test_csrf_masked(self) -> None:
        data = {"csrf_token": "abc"}
        result = mask_sensitive_data(data)
        assert result["csrf_token"] == "****"


class TestMaskStringSecrets:
    """Tests for mask_string_secrets."""

    def test_masks_bearer_token(self) -> None:
        text = "Authorization: Bearer my_token_abc123"
        result = mask_string_secrets(text)
        assert "Bearer ****" in result
        assert "my_token_abc123" not in result

    def test_masks_api_key_in_query(self) -> None:
        text = 'api_key: "sk-12345abc"'
        result = mask_string_secrets(text)
        assert "sk-12345abc" not in result

    def test_masks_password_in_url(self) -> None:
        text = "postgres://admin:secretpassword@localhost/mydb"
        result = mask_string_secrets(text)
        assert "secretpassword" not in result
        assert "admin" in result
        assert "localhost" in result

    def test_no_secrets_unchanged(self) -> None:
        text = "Hello world, no secrets here."
        result = mask_string_secrets(text)
        assert result == text

    def test_custom_mask(self) -> None:
        text = "Bearer abc123xyz"
        result = mask_string_secrets(text, mask="[HIDDEN]")
        assert "Bearer [HIDDEN]" in result
