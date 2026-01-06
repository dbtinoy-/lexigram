"""Tests for guard constants — thresholds, error codes, and metric names."""

from __future__ import annotations

import pytest
from lexigram.ai.guard import constants


class TestEnvironmentConstants:
    """Tests for environment variable configuration constants."""

    def test_env_prefix(self) -> None:
        assert constants.ENV_PREFIX == "LEX_AI_GUARD__"

    def test_env_nested_delimiter(self) -> None:
        assert constants.ENV_NESTED_DELIMITER == "__"


class TestDefaultThresholds:
    """Tests for default safety threshold constants."""

    def test_default_detection_threshold(self) -> None:
        assert constants.DEFAULT_DETECTION_THRESHOLD == 0.85
        assert isinstance(constants.DEFAULT_DETECTION_THRESHOLD, float)

    def test_default_detection_threshold_in_valid_range(self) -> None:
        assert 0.0 <= constants.DEFAULT_DETECTION_THRESHOLD <= 1.0

    def test_default_max_input_length(self) -> None:
        assert constants.DEFAULT_MAX_INPUT_LENGTH == 32_768
        assert isinstance(constants.DEFAULT_MAX_INPUT_LENGTH, int)

    def test_default_max_output_length(self) -> None:
        assert constants.DEFAULT_MAX_OUTPUT_LENGTH == 16_384
        assert isinstance(constants.DEFAULT_MAX_OUTPUT_LENGTH, int)


class TestErrorCodes:
    """Tests for error code constants."""

    def test_error_input_guard_violation(self) -> None:
        assert constants.ERROR_INPUT_GUARD_VIOLATION == "LEX_GUARD_001"

    def test_error_output_guard_violation(self) -> None:
        assert constants.ERROR_OUTPUT_GUARD_VIOLATION == "LEX_GUARD_002"

    def test_error_guard_config_invalid(self) -> None:
        assert constants.ERROR_GUARD_CONFIG_INVALID == "LEX_GUARD_003"

    def test_error_codes_are_strings(self) -> None:
        assert isinstance(constants.ERROR_INPUT_GUARD_VIOLATION, str)
        assert isinstance(constants.ERROR_OUTPUT_GUARD_VIOLATION, str)
        assert isinstance(constants.ERROR_GUARD_CONFIG_INVALID, str)

    def test_error_codes_are_unique(self) -> None:
        codes = [
            constants.ERROR_INPUT_GUARD_VIOLATION,
            constants.ERROR_OUTPUT_GUARD_VIOLATION,
            constants.ERROR_GUARD_CONFIG_INVALID,
        ]
        assert len(codes) == len(set(codes))


class TestMetricNames:
    """Tests for metric name constants."""

    def test_metric_guard_checks_total(self) -> None:
        assert constants.METRIC_GUARD_CHECKS_TOTAL == "ai.guard.checks.total"

    def test_metric_guard_violations_total(self) -> None:
        assert constants.METRIC_GUARD_VIOLATIONS_TOTAL == "ai.guard.violations.total"

    def test_metric_guard_check_duration_ms(self) -> None:
        assert constants.METRIC_GUARD_CHECK_DURATION_MS == "ai.guard.check.duration_ms"

    def test_metric_names_start_with_prefix(self) -> None:
        for metric in [
            constants.METRIC_GUARD_CHECKS_TOTAL,
            constants.METRIC_GUARD_VIOLATIONS_TOTAL,
            constants.METRIC_GUARD_CHECK_DURATION_MS,
        ]:
            assert metric.startswith("ai.guard.")


class TestVersion:
    """Tests for __version__ constant."""

    def test_version_is_string(self) -> None:
        assert isinstance(constants.__version__, str)

    def test_version_format(self) -> None:
        version = constants.__version__
        assert version.count(".") >= 2


class TestAllExports:
    """Tests to verify all expected constants are exported."""

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("DEFAULT_DETECTION_THRESHOLD", 0.85),
            ("DEFAULT_MAX_INPUT_LENGTH", 32768),
            ("DEFAULT_MAX_OUTPUT_LENGTH", 16384),
            ("ENV_NESTED_DELIMITER", "__"),
            ("ENV_PREFIX", "LEX_AI_GUARD__"),
            ("ERROR_GUARD_CONFIG_INVALID", "LEX_GUARD_003"),
            ("ERROR_INPUT_GUARD_VIOLATION", "LEX_GUARD_001"),
            ("ERROR_OUTPUT_GUARD_VIOLATION", "LEX_GUARD_002"),
            ("METRIC_GUARD_CHECKS_TOTAL", "ai.guard.checks.total"),
            ("METRIC_GUARD_CHECK_DURATION_MS", "ai.guard.check.duration_ms"),
            ("METRIC_GUARD_VIOLATIONS_TOTAL", "ai.guard.violations.total"),
        ],
    )
    def test_constant_exported(self, name: str, expected: str | int | float) -> None:
        assert hasattr(constants, name)
        assert getattr(constants, name) == expected