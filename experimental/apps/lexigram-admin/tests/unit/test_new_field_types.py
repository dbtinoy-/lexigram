"""Tests for rich field types (schema) and language switcher."""

from __future__ import annotations

from lexigram.admin.ui.organisms.topbar import LanguageSwitcher

# ---------------------------------------------------------------------------
# LanguageSwitcher
# ---------------------------------------------------------------------------


class TestLanguageSwitcher:
    def test_render_returns_component(self) -> None:
        sw = LanguageSwitcher(
            locales=[("en", "English"), ("fr", "Français")],
            current_locale="en",
        )
        html = str(sw.render())
        assert html is not None

    def test_contains_locale_options(self) -> None:
        sw = LanguageSwitcher(
            locales=[("en", "English"), ("de", "Deutsch")],
            current_locale="de",
        )
        html = str(sw.render())
        assert "en" in html
        assert "de" in html

    def test_action_url_in_form(self) -> None:
        sw = LanguageSwitcher(
            locales=[("en", "English")],
            action_url="/set-lang",
        )
        html = str(sw.render())
        assert "/set-lang" in html

    def test_csrf_token_in_plain_form(self) -> None:
        html = str(LanguageSwitcher(csrf_token="locale-token").render())
        assert 'name="csrf_token"' in html
        assert 'value="locale-token"' in html

    def test_default_action_url(self) -> None:
        sw = LanguageSwitcher()
        html = str(sw.render())
        assert "/admin/set-locale" in html

    def test_current_locale_selected(self) -> None:
        sw = LanguageSwitcher(
            locales=[("en", "English"), ("fr", "Français")],
            current_locale="fr",
        )
        html = str(sw.render())
        assert "fr" in html

    def test_contains_form_element(self) -> None:
        sw = LanguageSwitcher()
        html = str(sw.render())
        assert "form" in html.lower()

    def test_contains_select_element(self) -> None:
        sw = LanguageSwitcher(locales=[("en", "English")])
        html = str(sw.render())
        assert "select" in html.lower()

    def test_multiple_locales(self) -> None:
        locales = [
            ("en", "English"),
            ("fr", "Français"),
            ("es", "Español"),
            ("de", "Deutsch"),
        ]
        sw = LanguageSwitcher(locales=locales, current_locale="es")
        html = str(sw.render())
        for code, _ in locales:
            assert code in html

    def test_default_locales(self) -> None:
        sw = LanguageSwitcher()
        assert len(sw.locales) >= 1
