"""Tests for governance constants."""

from __future__ import annotations

import pytest

from lexigram.ai.governance import constants


class TestEnvironmentConstants:
    """Tests for environment-related constants."""

    def test_env_prefix(self) -> None:
        """Verify ENV_PREFIX has correct value."""
        assert constants.ENV_PREFIX == "LEX_AI_GOVERNANCE__"

    def test_env_nested_delimiter(self) -> None:
        """Verify ENV_NESTED_DELIMITER has correct value."""
        assert constants.ENV_NESTED_DELIMITER == "__"

    def test_env_prefix_with_nested_delimiter(self) -> None:
        """Verify prefix concatenation works as expected."""
        full_prefix = constants.ENV_PREFIX + "TEST" + constants.ENV_NESTED_DELIMITER + "VALUE"
        assert full_prefix == "LEX_AI_GOVERNANCE__TEST__VALUE"


class TestBudgetConstants:
    """Tests for budget-related constants."""

    def test_default_soft_limit_pct(self) -> None:
        """Verify DEFAULT_SOFT_LIMIT_PCT is 80%."""
        assert constants.DEFAULT_SOFT_LIMIT_PCT == 0.8

    def test_default_soft_limit_pct_is_fraction(self) -> None:
        """Verify soft limit is a valid fraction."""
        assert 0.0 <= constants.DEFAULT_SOFT_LIMIT_PCT <= 1.0

    def test_max_monthly_budget(self) -> None:
        """Verify MAX_MONTHLY_BUDGET is 100k."""
        assert constants.MAX_MONTHLY_BUDGET == 100_000.0

    def test_max_monthly_budget_is_positive(self) -> None:
        """Verify max budget is positive."""
        assert constants.MAX_MONTHLY_BUDGET > 0

    def test_soft_limit_calculated_correctly(self) -> None:
        """Verify soft limit is 80% of max budget."""
        expected_soft_limit = constants.MAX_MONTHLY_BUDGET * constants.DEFAULT_SOFT_LIMIT_PCT
        assert expected_soft_limit == 80_000.0


class TestRateLimitConstants:
    """Tests for rate-limit constants."""

    def test_default_rpm_limit(self) -> None:
        """Verify DEFAULT_RPM_LIMIT is 60."""
        assert constants.DEFAULT_RPM_LIMIT == 60

    def test_default_rpm_limit_is_positive(self) -> None:
        """Verify RPM limit is positive."""
        assert constants.DEFAULT_RPM_LIMIT > 0

    def test_default_tpm_limit(self) -> None:
        """Verify DEFAULT_TPM_LIMIT is 100k."""
        assert constants.DEFAULT_TPM_LIMIT == 100_000

    def test_default_tpm_limit_is_positive(self) -> None:
        """Verify TPM limit is positive."""
        assert constants.DEFAULT_TPM_LIMIT > 0

    def test_rpm_window_seconds(self) -> None:
        """Verify RPM_WINDOW_SECONDS is 60.0."""
        assert constants.RPM_WINDOW_SECONDS == 60.0

    def test_rpm_window_is_positive(self) -> None:
        """Verify RPM window is positive."""
        assert constants.RPM_WINDOW_SECONDS > 0


class TestPersistenceConstants:
    """Tests for persistence constants."""

    def test_spend_ttl_seconds(self) -> None:
        """Verify SPEND_TTL_SECONDS is ~32 days in seconds."""
        assert constants.SPEND_TTL_SECONDS == 32 * 24 * 3600

    def test_spend_ttl_seconds_calculation(self) -> None:
        """Verify TTL calculation: 32 days = 2764800 seconds."""
        expected = 32 * 24 * 3600
        assert constants.SPEND_TTL_SECONDS == expected

    def test_spend_ttl_is_positive(self) -> None:
        """Verify spend TTL is positive."""
        assert constants.SPEND_TTL_SECONDS > 0


class TestVersion:
    """Tests for version constant."""

    def test_version_exists(self) -> None:
        """Verify __version__ exists."""
        assert hasattr(constants, "__version__")

    def test_version_is_string(self) -> None:
        """Verify __version__ is a string."""
        assert isinstance(constants.__version__, str)

    def test_version_format(self) -> None:
        """Verify version follows semver-like format."""
        version = constants.__version__
        assert version.count(".") >= 2


class TestAllExports:
    """Tests for __all__ exports."""

    def test_all_contains_default_rpm_limit(self) -> None:
        """Verify DEFAULT_RPM_LIMIT is in __all__."""
        assert "DEFAULT_RPM_LIMIT" in constants.__all__

    def test_all_contains_default_soft_limit_pct(self) -> None:
        """Verify DEFAULT_SOFT_LIMIT_PCT is in __all__."""
        assert "DEFAULT_SOFT_LIMIT_PCT" in constants.__all__

    def test_all_contains_default_tpm_limit(self) -> None:
        """Verify DEFAULT_TPM_LIMIT is in __all__."""
        assert "DEFAULT_TPM_LIMIT" in constants.__all__

    def test_all_contains_env_nested_delimiter(self) -> None:
        """Verify ENV_NESTED_DELIMITER is in __all__."""
        assert "ENV_NESTED_DELIMITER" in constants.__all__

    def test_all_contains_env_prefix(self) -> None:
        """Verify ENV_PREFIX is in __all__."""
        assert "ENV_PREFIX" in constants.__all__

    def test_all_contains_max_monthly_budget(self) -> None:
        """Verify MAX_MONTHLY_BUDGET is in __all__."""
        assert "MAX_MONTHLY_BUDGET" in constants.__all__

    def test_all_contains_rpm_window_seconds(self) -> None:
        """Verify RPM_WINDOW_SECONDS is in __all__."""
        assert "RPM_WINDOW_SECONDS" in constants.__all__

    def test_all_contains_spend_ttl_seconds(self) -> None:
        """Verify SPEND_TTL_SECONDS is in __all__."""
        assert "SPEND_TTL_SECONDS" in constants.__all__

    def test_all_contains_version(self) -> None:
        """Verify __version__ is in __all__."""
        assert "__version__" in constants.__all__

    def test_all_exports_count(self) -> None:
        """Verify __all__ has expected number of exports."""
        assert len(constants.__all__) == 9