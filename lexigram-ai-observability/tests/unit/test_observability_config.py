"""Tests for ObservabilityConfig."""

import pytest

from lexigram.ai.observability.config import ObservabilityConfig
from lexigram.contracts.core.config import ConfigIssue, Environment


class TestObservabilityConfigDefaults:
    """Test default configuration values."""

    def test_enabled_defaults_to_true(self):
        config = ObservabilityConfig()
        assert config.enabled is True

    def test_metrics_enabled_defaults_to_true(self):
        config = ObservabilityConfig()
        assert config.metrics_enabled is True

    def test_tracing_enabled_defaults_to_true(self):
        config = ObservabilityConfig()
        assert config.tracing_enabled is True

    def test_health_checks_enabled_defaults_to_true(self):
        config = ObservabilityConfig()
        assert config.health_checks_enabled is True


class TestObservabilityConfigEnvironmentOverrides:
    """Test environment variable overrides.

    Note: Full env var testing requires integration test setup.
    These tests verify basic config initialization works.
    """

    def test_config_can_be_instantiated(self):
        config = ObservabilityConfig()
        assert config is not None


class TestObservabilityConfigValidation:
    """Test configuration validation for different environments."""

    def test_production_no_issues_when_all_enabled(self):
        config = ObservabilityConfig(
            enabled=True,
            metrics_enabled=True,
            tracing_enabled=True,
        )
        issues = config.validate_for_environment(Environment.PRODUCTION)
        assert issues == []

    def test_production_warns_when_tracing_disabled(self):
        config = ObservabilityConfig(
            enabled=True,
            metrics_enabled=True,
            tracing_enabled=False,
        )
        issues = config.validate_for_environment(Environment.PRODUCTION)
        assert len(issues) == 1
        assert issues[0].field == "tracing_enabled"
        assert issues[0].severity == "warning"

    def test_production_warns_when_metrics_disabled(self):
        config = ObservabilityConfig(
            enabled=True,
            metrics_enabled=False,
            tracing_enabled=True,
        )
        issues = config.validate_for_environment(Environment.PRODUCTION)
        assert len(issues) == 1
        assert issues[0].field == "metrics_enabled"
        assert issues[0].severity == "warning"

    def test_production_warns_when_both_disabled(self):
        config = ObservabilityConfig(
            enabled=True,
            metrics_enabled=False,
            tracing_enabled=False,
        )
        issues = config.validate_for_environment(Environment.PRODUCTION)
        assert len(issues) == 2

    def test_development_no_warnings(self):
        config = ObservabilityConfig(
            enabled=True,
            metrics_enabled=False,
            tracing_enabled=False,
        )
        issues = config.validate_for_environment(Environment.DEVELOPMENT)
        assert issues == []

    def test_test_no_warnings(self):
        config = ObservabilityConfig(
            enabled=True,
            metrics_enabled=False,
            tracing_enabled=False,
        )
        issues = config.validate_for_environment(Environment.TEST)
        assert issues == []


class TestObservabilityConfigConfigSection:
    """Test config section name."""

    def test_config_section_name(self):
        assert ObservabilityConfig.config_section == "ai_observability"