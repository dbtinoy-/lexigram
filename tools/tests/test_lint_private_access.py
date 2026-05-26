"""Private-access lint tool tests."""

from __future__ import annotations

import textwrap

from tools.lint_private_access import scan_source


def _mod(source: str, filename: str = "lexigram/web/routing/pipeline.py") -> list[str]:
    return scan_source(textwrap.dedent(source), filename)


def test_private_import_detected() -> None:
    hits = _mod(
        """\
        from lexigram.admin.auth.store import _ensure
        """
    )
    assert hits, "cross-package private import must be flagged"


def test_same_package_private_import_allowed() -> None:
    hits = _mod(
        """\
        from lexigram.admin.auth.store import _ensure
        """,
        filename="lexigram/admin/auth/services/panel.py",
    )
    assert hits == [], "same-package private import must be allowed"


def test_self_private_attribute_ignored() -> None:
    hits = _mod(
        """\
        def f(self):
            return self._cache
        """
    )
    assert hits == []
