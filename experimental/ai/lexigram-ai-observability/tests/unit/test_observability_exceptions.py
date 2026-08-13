"""Tests for observability exceptions."""

import pytest

from lexigram.ai.observability.exceptions import (
    HealthCheckError,
    MetricsError,
    ObservabilityError,
    TracingError,
)
from lexigram.contracts.ai.exceptions import AIError


class TestObservabilityError:
    """Test ObservabilityError base exception."""

    def test_inherits_from_ai_error(self):
        assert issubclass(ObservabilityError, AIError)

    def test_has_error_code(self):
        error = ObservabilityError("test message")
        assert error._code == "LEX_ERR_OBS_001"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(ObservabilityError):
            raise ObservabilityError("test")


class TestHealthCheckError:
    """Test HealthCheckError exception."""

    def test_inherits_from_observability_error(self):
        assert issubclass(HealthCheckError, ObservabilityError)

    def test_has_error_code(self):
        error = HealthCheckError("health check failed")
        assert error._code == "LEX_ERR_OBS_002"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(HealthCheckError):
            raise HealthCheckError("health check failed")


class TestMetricsError:
    """Test MetricsError exception."""

    def test_inherits_from_observability_error(self):
        assert issubclass(MetricsError, ObservabilityError)

    def test_has_error_code(self):
        error = MetricsError("metrics failed")
        assert error._code == "LEX_ERR_OBS_003"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(MetricsError):
            raise MetricsError("metrics failed")


class TestTracingError:
    """Test TracingError exception."""

    def test_inherits_from_observability_error(self):
        assert issubclass(TracingError, ObservabilityError)

    def test_has_error_code(self):
        error = TracingError("tracing failed")
        assert error._code == "LEX_ERR_OBS_004"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(TracingError):
            raise TracingError("tracing failed")


class TestExceptionHierarchy:
    """Test exception hierarchy for catching."""

    def test_can_catch_all_observability_as_ai_error(self):
        """Verify we can catch all as AIError."""
        errors = [
            ObservabilityError("base"),
            HealthCheckError("health"),
            MetricsError("metrics"),
            TracingError("tracing"),
        ]
        for error in errors:
            assert isinstance(error, AIError)

    def test_can_catch_as_observability_error(self):
        """Verify catching as base ObservabilityError."""
        errors = [
            ObservabilityError("base"),
            HealthCheckError("health"),
            MetricsError("metrics"),
            TracingError("tracing"),
        ]
        for error in errors:
            assert isinstance(error, ObservabilityError)