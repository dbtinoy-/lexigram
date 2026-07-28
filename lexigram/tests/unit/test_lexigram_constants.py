"""Tests for lexigram package constants."""

from __future__ import annotations

from lexigram.constants import FEATURES, MIN_PYTHON_VERSION, __version__


class TestVersion:
    """Tests for version."""

    def test_version_is_string(self) -> None:
        assert isinstance(__version__, str)

    def test_version_format(self) -> None:
        parts = __version__.split(".")
        assert len(parts) >= 3


class TestMinPythonVersion:
    """Tests for minimum Python version."""

    def test_is_tuple(self) -> None:
        assert isinstance(MIN_PYTHON_VERSION, tuple)

    def test_has_two_parts(self) -> None:
        assert len(MIN_PYTHON_VERSION) == 2

    def test_major_is_3(self) -> None:
        assert MIN_PYTHON_VERSION[0] >= 3

    def test_minor_is_11_or_higher(self) -> None:
        assert MIN_PYTHON_VERSION[1] >= 11


class TestFeatures:
    """Tests for feature flags."""

    def test_features_is_dict(self) -> None:
        assert isinstance(FEATURES, dict)

    def test_has_result_chaining(self) -> None:
        assert "result_chaining" in FEATURES

    def test_has_lazy_imports(self) -> None:
        assert "lazy_imports" in FEATURES

    def test_has_strict_injection(self) -> None:
        assert "strict_injection" in FEATURES

    def test_has_module_visibility(self) -> None:
        assert "module_visibility" in FEATURES

    def test_all_features_are_bools(self) -> None:
        for value in FEATURES.values():
            assert isinstance(value, bool)
