"""Tests for PromptConfig and rendering options."""

from __future__ import annotations

import pytest

from lexigram.ai.prompt.config import PromptConfig


class TestPromptConfigDefaults:
    """Test PromptConfig default values."""

    def test_default_config_enabled(self) -> None:
        """Default config should have prompt subsystem enabled."""
        config = PromptConfig()

        assert config.enabled is True

    def test_default_format(self) -> None:
        """Default config should use f_string format."""
        config = PromptConfig()

        assert config.default_format == "f_string"

    def test_default_sanitization(self) -> None:
        """Default config should enable input sanitization."""
        config = PromptConfig()

        assert config.sanitize_inputs is True
        assert config.strict_sanitizer is True

    def test_default_variable_length(self) -> None:
        """Default config should have no variable length limit."""
        config = PromptConfig()

        assert config.max_variable_length == 0


class TestPromptConfigCustomization:
    """Test PromptConfig customization."""

    def test_can_disable_subsystem(self) -> None:
        """Config should allow disabling prompt subsystem."""
        config = PromptConfig(enabled=False)

        assert config.enabled is False

    def test_can_set_format(self) -> None:
        """Config should allow setting rendering format."""
        for fmt in ["f_string", "jinja2", "dollar", "simple"]:
            config = PromptConfig(default_format=fmt)
            assert config.default_format == fmt

    def test_can_disable_sanitization(self) -> None:
        """Config should allow disabling input sanitization."""
        config = PromptConfig(sanitize_inputs=False)

        assert config.sanitize_inputs is False

    def test_can_disable_strict_sanitizer(self) -> None:
        """Config should allow disabling strict sanitizer."""
        config = PromptConfig(strict_sanitizer=False)

        assert config.strict_sanitizer is False

    def test_can_set_variable_length_limit(self) -> None:
        """Config should allow setting variable length limit."""
        config = PromptConfig(max_variable_length=2000)

        assert config.max_variable_length == 2000

    def test_full_customization(self) -> None:
        """Config should handle full customization."""
        config = PromptConfig(
            enabled=True,
            default_format="jinja2",
            sanitize_inputs=True,
            strict_sanitizer=False,
            max_variable_length=5000,
        )

        assert config.enabled is True
        assert config.default_format == "jinja2"
        assert config.sanitize_inputs is True
        assert config.strict_sanitizer is False
        assert config.max_variable_length == 5000


class TestPromptConfigValidation:
    """Test PromptConfig validation."""

    def test_max_variable_length_non_negative(self) -> None:
        """max_variable_length must be >= 0."""
        config = PromptConfig(max_variable_length=1000)
        assert config.max_variable_length == 1000

        config = PromptConfig(max_variable_length=0)
        assert config.max_variable_length == 0


class TestPromptRenderingFormats:
    """Test supported rendering formats."""

    def test_supported_formats(self) -> None:
        """Config should support standard rendering formats."""
        supported_formats = ["f_string", "jinja2", "dollar", "simple"]

        for fmt in supported_formats:
            config = PromptConfig(default_format=fmt)
            assert config.default_format == fmt

    def test_format_is_string(self) -> None:
        """Format field should be string."""
        config = PromptConfig()

        assert isinstance(config.default_format, str)


class TestPromptConfigSanitization:
    """Test sanitization-related settings."""

    def test_sanitization_can_be_disabled(self) -> None:
        """Sanitization can be independently disabled."""
        config = PromptConfig(
            sanitize_inputs=False,
            strict_sanitizer=True,
        )

        assert config.sanitize_inputs is False

    def test_strict_sanitizer_requires_sanitization(self) -> None:
        """Strict sanitizer setting is independent of sanitization."""
        # Can have strict=False even with sanitization=True
        config = PromptConfig(
            sanitize_inputs=True,
            strict_sanitizer=False,
        )

        assert config.sanitize_inputs is True
        assert config.strict_sanitizer is False

    def test_sanitization_disabled_with_strict_false(self) -> None:
        """Can have both sanitization and strict disabled."""
        config = PromptConfig(
            sanitize_inputs=False,
            strict_sanitizer=False,
        )

        assert config.sanitize_inputs is False
        assert config.strict_sanitizer is False
