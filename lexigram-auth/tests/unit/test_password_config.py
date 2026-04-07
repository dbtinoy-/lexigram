"""Tests for PasswordConfig in AuthConfig."""

from __future__ import annotations

from lexigram.auth.config import AuthConfig, PasswordConfig


class TestPasswordConfigDefaults:
    def test_default_min_length(self) -> None:
        config = PasswordConfig()
        assert config.min_length == 12

    def test_default_max_length(self) -> None:
        config = PasswordConfig()
        assert config.max_length == 128

    def test_complexity_flags_defaults(self) -> None:
        config = PasswordConfig()
        assert config.require_uppercase  # True by default
        assert not config.require_lowercase  # False by default
        assert config.require_digits  # True by default
        assert not config.require_special  # False by default

    def test_banned_patterns_empty_by_default(self) -> None:
        config = PasswordConfig()
        assert config.banned_patterns == []

    def test_custom_values(self) -> None:
        config = PasswordConfig(
            min_length=12,
            max_length=64,
            require_uppercase=True,
            require_digits=True,
            banned_patterns=["password", "letmein"],
        )
        assert config.min_length == 12
        assert config.max_length == 64
        assert config.require_uppercase
        assert config.require_digits
        assert "password" in config.banned_patterns


class TestAuthConfigPassword:
    def test_password_field_has_default(self) -> None:
        """AuthConfig must expose a `password` field with a PasswordConfig default."""
        config = AuthConfig(secret_key="test-key", token={"secret_key": "test-key"})
        assert isinstance(config.password, PasswordConfig)

    def test_password_field_is_configurable(self) -> None:
        config = AuthConfig(
            secret_key="test-key",
            token={"secret_key": "test-key"},
            password={"min_length": 16, "require_digits": True},
        )
        assert config.password.min_length == 16
        assert config.password.require_digits
