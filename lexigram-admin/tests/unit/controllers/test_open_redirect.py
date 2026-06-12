"""Unit tests for AuthController._safe_next_url (open-redirect guard).

Covers the D1 helper from the open-redirect plan: a leading-`/`-only
allowlist that rejects absolute URLs, scheme-relative URLs, backslash
variants, and bare words, while passing legitimate relative paths
through unchanged.
"""

from __future__ import annotations

from lexigram.admin.controllers.auth import AuthController


class TestSafeNextUrl:
    def test_rejects_absolute_url(self) -> None:
        assert AuthController._safe_next_url("https://attacker.example/x") == "/admin/"

    def test_rejects_scheme_relative_url(self) -> None:
        assert AuthController._safe_next_url("//attacker.example/x") == "/admin/"

    def test_rejects_backslash_variant(self) -> None:
        assert AuthController._safe_next_url("/\\attacker.example/x") == "/admin/"

    def test_passes_legitimate_relative_path(self) -> None:
        assert (
            AuthController._safe_next_url("/admin/profile/mfa") == "/admin/profile/mfa"
        )

    def test_passes_default_path(self) -> None:
        assert AuthController._safe_next_url("/admin/") == "/admin/"

    def test_empty_string_defaults(self) -> None:
        assert AuthController._safe_next_url("") == "/admin/"

    def test_bare_word_defaults(self) -> None:
        assert AuthController._safe_next_url("attacker.example") == "/admin/"
