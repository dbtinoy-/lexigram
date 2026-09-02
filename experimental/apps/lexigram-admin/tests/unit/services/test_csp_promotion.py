"""CSP promotion analysis tests (R48, docs/09-01-2026/44-csp-enforcement-flip.md)."""

from __future__ import annotations

from lexigram.admin.services.security.promotion import (
    parse_directives,
    ui_compat_blockers,
)
from lexigram.admin.settings.panel.models import DEFAULT_CSP, STRICT_CSP


class TestParseDirectives:
    def test_basic_split(self) -> None:
        parsed = parse_directives("default-src 'self'; script-src 'self' 'unsafe-eval'")
        assert parsed == {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-eval'"],
        }

    def test_tolerates_whitespace_and_empty_segments(self) -> None:
        parsed = parse_directives("  default-src 'self' ;;  ; script-src 'self'  ")
        assert set(parsed) == {"default-src", "script-src"}

    def test_duplicate_directive_keeps_first(self) -> None:
        parsed = parse_directives("script-src 'self'; script-src 'unsafe-eval'")
        assert parsed["script-src"] == ["'self'"]

    def test_directive_names_lowercased(self) -> None:
        assert "script-src" in parse_directives("SCRIPT-SRC 'self'")

    def test_empty_and_none_safe(self) -> None:
        assert parse_directives("") == {}
        assert parse_directives(None) == {}  # type: ignore[arg-type]


class TestUiCompatBlockers:
    def test_default_csp_has_no_blockers(self) -> None:
        """The shipped enforced policy must always be flip-safe (B14)."""
        assert ui_compat_blockers(DEFAULT_CSP) == []

    def test_strict_csp_flags_all_three(self) -> None:
        blockers = ui_compat_blockers(STRICT_CSP)
        text = " ".join(blockers)
        assert len(blockers) == 3
        assert "'unsafe-eval'" in text
        assert "script-src lacks 'unsafe-inline'" in text
        assert "style-src lacks 'unsafe-inline'" in text

    def test_default_src_fallback_applies(self) -> None:
        """No script-src ⇒ default-src governs scripts."""
        blockers = ui_compat_blockers("default-src 'self'")
        assert any("'unsafe-eval'" in b for b in blockers)

    def test_no_restriction_means_no_blockers(self) -> None:
        """Neither script-src nor default-src ⇒ browser applies none."""
        assert ui_compat_blockers("img-src 'self'") == []

    def test_nonce_source_satisfies_inline_scripts(self) -> None:
        blockers = ui_compat_blockers(
            "script-src 'self' 'unsafe-eval' 'nonce-abc123'; "
            "style-src 'self' 'unsafe-inline'"
        )
        assert blockers == []

    def test_hash_source_satisfies_inline_styles(self) -> None:
        blockers = ui_compat_blockers(
            "script-src 'self' 'unsafe-eval' 'unsafe-inline'; "
            "style-src 'self' 'sha256-deadbeef'"
        )
        assert blockers == []
