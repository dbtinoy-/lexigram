"""P1 structural test: lexigram-storage must use `backends/` and `lib/`."""

from __future__ import annotations

from pathlib import Path

import pytest

_SRC_ROOT = Path(__file__).parents[2] / "src" / "lexigram" / "storage"


class TestStorageDirectoryStructure:
    """Assert that drivers/ → backends/ and utils/ → lib/ renames are complete."""

    def test_backends_directory_exists(self) -> None:
        assert (_SRC_ROOT / "backends").is_dir(), (
            "src/lexigram/storage/backends/ must exist"
        )

    def test_drivers_directory_does_not_exist(self) -> None:
        assert not (_SRC_ROOT / "drivers").exists(), (
            "src/lexigram/storage/drivers/ must not exist (renamed to backends/)"
        )

    def test_lib_directory_exists(self) -> None:
        assert (_SRC_ROOT / "lib").is_dir(), (
            "src/lexigram/storage/lib/ must exist"
        )

    def test_utils_directory_does_not_exist(self) -> None:
        assert not (_SRC_ROOT / "utils").exists(), (
            "src/lexigram/storage/utils/ must not exist (renamed to lib/)"
        )
