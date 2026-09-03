"""Tests for the shared user-facing error humanizer (roadmap R4)."""

from __future__ import annotations

from lexigram.admin.controllers._errors import humanize_error


class TestHumanizeError:
    def test_strips_leading_code(self) -> None:
        assert (
            humanize_error("[LEX_ERR_ADMIN_009] Something went wrong.")
            == "Something went wrong."
        )

    def test_strips_embedded_codes_in_chained_errors(self) -> None:
        chained = (
            "[LEX_ERR_ADMIN_010] Verification email could not be delivered: "
            "[LEX_ERR_ADMIN_009] All 1 recipient(s) failed."
        )
        result = humanize_error(chained)
        assert "LEX_ERR" not in result
        assert "Verification email could not be delivered" in result
        assert "All 1 recipient(s) failed" in result

    def test_strips_fix_and_see_annotations(self) -> None:
        message = (
            "[LEX_ERR_DI_004] 'Thing' is not registered.\n"
            "  → Fix: Verify the type is registered in a Provider.\n"
            "  → See: https://docs.lexigram.dev/reference/errors/LEX_ERR_DI_004"
        )
        result = humanize_error(message)
        assert "LEX_ERR" not in result
        assert "→" not in result
        assert "docs.lexigram.dev" not in result
        assert "'Thing' is not registered." in result

    def test_collapses_to_single_line(self) -> None:
        result = humanize_error("line one\n   line two\n\nline three")
        assert result == "line one line two line three"

    def test_empty_returns_fallback(self) -> None:
        assert humanize_error("", fallback="oops") == "oops"
        assert humanize_error("") == ""

    def test_annotation_only_message_returns_fallback(self) -> None:
        result = humanize_error(
            "[LEX_ERR_X_001] → See: https://docs.example",
            fallback="an internal error occurred.",
        )
        assert result == "an internal error occurred."

    def test_plain_message_unchanged(self) -> None:
        assert humanize_error("Invalid credentials.") == "Invalid credentials."

    def test_legacy_alias_delegates(self) -> None:
        from lexigram.admin.controllers.auth.core import _humanize_error

        chained = "[LEX_ERR_A_1] outer: [LEX_ERR_B_2] inner → See: x"
        result = _humanize_error(chained)
        assert "LEX_ERR" not in result
        assert "outer:" in result and "inner" in result
