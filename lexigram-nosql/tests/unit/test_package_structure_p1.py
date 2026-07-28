"""Structural test for P1 Data Task 2: drivers renamed to backends.

Asserts that:
- ``src/lexigram/nosql/backends`` exists (root backends tree)
- ``src/lexigram/nosql/drivers`` does NOT exist
- ``src/lexigram/nosql/graph`` does NOT exist (moved to lexigram-graph)
"""

from __future__ import annotations

from pathlib import Path

# Resolve the package source root relative to this test file.
_NOSQL_SRC = Path(__file__).parent.parent.parent / "src" / "lexigram" / "nosql"


class TestNoSQLBackendsPackageStructure:
    def test_root_backends_directory_exists(self) -> None:
        assert (_NOSQL_SRC / "backends").is_dir(), (
            "src/lexigram/nosql/backends/ must exist after rename"
        )

    def test_root_drivers_directory_does_not_exist(self) -> None:
        assert not (_NOSQL_SRC / "drivers").exists(), (
            "src/lexigram/nosql/drivers/ must be removed after rename"
        )

    def test_graph_directory_does_not_exist(self) -> None:
        assert not (_NOSQL_SRC / "graph").exists(), (
            "src/lexigram/nosql/graph/ must be removed — moved to lexigram-graph package"
        )
