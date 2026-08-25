"""Unit tests for dev.checks.version pure version math.

Pins the §3.6 scheme: within an active series only the build segment
moves (0.1.5001 → 0.1.5002); a bare patch starts a fresh series at 001
(0.1.4 → 0.1.4001).
"""

from __future__ import annotations

import pytest

from dev.checks.version import format_version, next_version, split_version


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("0.1.5001", (1, 5, 1)),
        ("0.1.4", (1, 4, 0)),
        ("0.1.3007", (1, 3, 7)),
    ],
)
def test_split_version(version: str, expected: tuple[int, int, int]) -> None:
    assert split_version(version) == expected


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("0.1.5001", "0.1.5002"),
        ("0.1.5009", "0.1.5010"),
        # Bare patch starts its own build series — never promotes patch.
        ("0.1.4", "0.1.4001"),
    ],
)
def test_next_version_build_bump(version: str, expected: str) -> None:
    assert next_version(version, bump="build") == expected


def test_next_version_patch_and_minor() -> None:
    assert next_version("0.1.5007", bump="patch") == "0.1.6001"
    assert next_version("0.1.5007", bump="minor") == "0.2.1001"


def test_format_version_omits_zero_build() -> None:
    assert format_version(1, 4, 0) == "0.1.4"
    assert format_version(1, 5, 12) == "0.1.5012"


def test_series_continuity_regression() -> None:
    """Guard the historical mistake: 0.1.4 must NOT become 0.1.5001."""
    assert next_version("0.1.4") != "0.1.5001"
