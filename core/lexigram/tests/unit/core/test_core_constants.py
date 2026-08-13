"""Tests for lexigram.constants module - package-level constants."""

from __future__ import annotations

import pytest

from lexigram import constants


class TestVersion:
    """Test version metadata."""

    def test_version_is_string(self) -> None:
        """__version__ should be a string."""
        assert isinstance(constants.__version__, str)

    def test_version_format(self) -> None:
        """__version__ should follow semantic versioning format."""
        version = constants.__version__
        parts = version.split(".")
        assert len(parts) >= 3, f"Version '{version}' should have at least 3 parts"
        for part in parts:
            assert part.isdigit(), f"Version part '{part}' should be numeric"


class TestPythonVersion:
    """Test Python version requirements."""

    def test_min_python_version_is_tuple(self) -> None:
        """MIN_PYTHON_VERSION should be a tuple of two ints."""
        assert isinstance(constants.MIN_PYTHON_VERSION, tuple)
        assert len(constants.MIN_PYTHON_VERSION) == 2
        major, minor = constants.MIN_PYTHON_VERSION
        assert isinstance(major, int)
        assert isinstance(minor, int)

    def test_min_python_version_value(self) -> None:
        """MIN_PYTHON_VERSION should be (3, 11)."""
        assert constants.MIN_PYTHON_VERSION == (3, 11)


class TestFeatureFlags:
    """Test feature flags dictionary."""

    def test_features_is_dict(self) -> None:
        """FEATURES should be a dictionary."""
        assert isinstance(constants.FEATURES, dict)

    def test_features_contains_result_chaining(self) -> None:
        """FEATURES should contain result_chaining flag."""
        assert "result_chaining" in constants.FEATURES

    def test_features_contains_lazy_imports(self) -> None:
        """FEATURES should contain lazy_imports flag."""
        assert "lazy_imports" in constants.FEATURES

    def test_features_contains_strict_injection(self) -> None:
        """FEATURES should contain strict_injection flag."""
        assert "strict_injection" in constants.FEATURES

    def test_features_contains_module_visibility(self) -> None:
        """FEATURES should contain module_visibility flag."""
        assert "module_visibility" in constants.FEATURES

    def test_feature_flags_are_bools(self) -> None:
        """All feature flag values should be booleans."""
        for key, value in constants.FEATURES.items():
            assert isinstance(value, bool), f"Feature '{key}' should be bool, got {type(value)}"

    def test_result_chaining_is_enabled(self) -> None:
        """result_chaining should be True."""
        assert constants.FEATURES["result_chaining"] is True

    def test_lazy_imports_is_enabled(self) -> None:
        """lazy_imports should be True."""
        assert constants.FEATURES["lazy_imports"] is True

    def test_strict_injection_is_enabled(self) -> None:
        """strict_injection should be True."""
        assert constants.FEATURES["strict_injection"] is True

    def test_module_visibility_is_disabled(self) -> None:
        """module_visibility should be False (future feature)."""
        assert constants.FEATURES["module_visibility"] is False


class TestExports:
    """Test that constants are properly exported."""

    def test_all_contains_min_python_version(self) -> None:
        """MIN_PYTHON_VERSION should be in __all__."""
        assert "MIN_PYTHON_VERSION" in constants.__all__

    def test_all_contains_features(self) -> None:
        """FEATURES should be in __all__."""
        assert "FEATURES" in constants.__all__