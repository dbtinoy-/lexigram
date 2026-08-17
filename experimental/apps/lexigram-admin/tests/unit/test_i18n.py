"""Tests for the i18n framework (Translator + get_locale)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.admin.i18n import Translator, get_locale


# ---------------------------------------------------------------------------
# Translator — basic
# ---------------------------------------------------------------------------

class TestTranslatorBasic:
    def test_translate_exact_match(self) -> None:
        t = Translator()
        t.load_catalog("en", {"greeting": "Hello!"})
        assert t.t("greeting", locale="en") == "Hello!"

    def test_shorthand_call(self) -> None:
        t = Translator()
        t.load_catalog("en", {"key": "Value"})
        assert t("key", locale="en") == "Value"

    def test_returns_key_when_missing(self) -> None:
        t = Translator()
        assert t.t("missing.key", locale="en") == "missing.key"

    def test_loaded_locales(self) -> None:
        t = Translator()
        t.load_catalog("en", {"k": "v"})
        t.load_catalog("fr", {"k": "v"})
        assert sorted(t.loaded_locales) == ["en", "fr"]

    def test_get_catalog_returns_copy(self) -> None:
        t = Translator()
        t.load_catalog("en", {"k": "v"})
        cat = t.get_catalog("en")
        cat["extra"] = "injected"
        assert "extra" not in t.get_catalog("en")

    def test_load_catalog_merges(self) -> None:
        t = Translator()
        t.load_catalog("en", {"a": "A"})
        t.load_catalog("en", {"b": "B"})
        assert t.t("a", locale="en") == "A"
        assert t.t("b", locale="en") == "B"


# ---------------------------------------------------------------------------
# Fallback chain
# ---------------------------------------------------------------------------

class TestFallbackChain:
    def test_region_falls_back_to_language(self) -> None:
        t = Translator(default_locale="en")
        t.load_catalog("fr", {"hello": "Bonjour"})
        assert t.t("hello", locale="fr-CA") == "Bonjour"

    def test_falls_back_to_default(self) -> None:
        t = Translator(default_locale="en")
        t.load_catalog("en", {"bye": "Goodbye"})
        assert t.t("bye", locale="de") == "Goodbye"

    def test_prefers_exact_locale_over_language(self) -> None:
        t = Translator(default_locale="en")
        t.load_catalog("fr", {"msg": "French"})
        t.load_catalog("fr-CA", {"msg": "Canadian French"})
        assert t.t("msg", locale="fr-CA") == "Canadian French"

    def test_no_fallback_when_default_is_missing(self) -> None:
        t = Translator(default_locale="zz")  # no catalog for "zz"
        result = t.t("nonexistent", locale="xx")
        assert result == "nonexistent"


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------

class TestInterpolation:
    def test_named_placeholder(self) -> None:
        t = Translator()
        t.load_catalog("en", {"welcome": "Welcome, {name}!"})
        assert t.t("welcome", locale="en", name="Alice") == "Welcome, Alice!"

    def test_multiple_placeholders(self) -> None:
        t = Translator()
        t.load_catalog("en", {"info": "{a} + {b} = {c}"})
        assert t.t("info", locale="en", a=1, b=2, c=3) == "1 + 2 = 3"

    def test_missing_placeholder_left_as_is(self) -> None:
        t = Translator()
        t.load_catalog("en", {"msg": "Hello {name}"})
        result = t.t("msg", locale="en")  # no name kwarg
        assert "{name}" in result


# ---------------------------------------------------------------------------
# Pluralisation
# ---------------------------------------------------------------------------

class TestPluralisation:
    def test_singular_count_one(self) -> None:
        t = Translator()
        t.load_catalog("en", {"items": "{count} item|{count} items"})
        assert t.t("items", locale="en", count=1) == "1 item"

    def test_plural_count_many(self) -> None:
        t = Translator()
        t.load_catalog("en", {"items": "{count} item|{count} items"})
        assert t.t("items", locale="en", count=5) == "5 items"

    def test_plural_count_zero(self) -> None:
        t = Translator()
        t.load_catalog("en", {"items": "{count} item|{count} items"})
        assert t.t("items", locale="en", count=0) == "0 items"

    def test_single_form_always_returned(self) -> None:
        t = Translator()
        t.load_catalog("en", {"status": "pending"})
        assert t.t("status", locale="en", count=5) == "pending"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

class TestFormattingHelpers:
    def test_format_number_integer(self) -> None:
        result = Translator.format_number(1234567)
        assert result == "1,234,567"

    def test_format_number_with_decimals(self) -> None:
        result = Translator.format_number(1234.5, decimals=2)
        assert result == "1,234.50"

    def test_format_currency_usd(self) -> None:
        result = Translator.format_currency(1234.56, "USD")
        assert result == "$1,234.56"

    def test_format_currency_eur(self) -> None:
        result = Translator.format_currency(99.0, "EUR")
        assert result == "€99.00"

    def test_format_currency_unknown_uses_code(self) -> None:
        result = Translator.format_currency(10.0, "XYZ")
        assert result.startswith("XYZ")

    def test_format_date(self) -> None:
        from datetime import date

        d = date(2024, 6, 15)
        assert Translator.format_date(d) == "2024-06-15"

    def test_format_date_custom_fmt(self) -> None:
        from datetime import date

        d = date(2024, 6, 15)
        assert Translator.format_date(d, fmt="%d/%m/%Y") == "15/06/2024"


# ---------------------------------------------------------------------------
# get_locale
# ---------------------------------------------------------------------------

class TestGetLocale:
    def test_returns_state_locale(self) -> None:
        request = MagicMock()
        request.state.locale = "de"
        assert get_locale(request) == "de"

    def test_returns_cookie_locale(self) -> None:
        request = MagicMock()
        del request.state.locale  # no state.locale
        request.cookies = {"admin_locale": "fr"}
        assert get_locale(request) == "fr"

    def test_returns_accept_language(self) -> None:
        request = MagicMock()
        request.state = MagicMock(spec=[])  # no .locale
        request.cookies = {}
        request.headers = {"accept-language": "fr-CA,fr;q=0.9,en;q=0.8"}
        assert get_locale(request) == "fr-CA"

    def test_returns_default_when_nothing_set(self) -> None:
        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.cookies = {}
        request.headers = {}
        assert get_locale(request, default="es") == "es"


# ---------------------------------------------------------------------------
# Base English catalog
# ---------------------------------------------------------------------------

class TestBaseEnglishCatalog:
    def test_base_catalog_loaded(self) -> None:
        from lexigram.admin.i18n import translator

        assert translator.t("admin.save", locale="en") == "Save"
        assert translator.t("admin.cancel", locale="en") == "Cancel"

    def test_plural_items_selected(self) -> None:
        from lexigram.admin.i18n import translator

        one = translator.t("admin.items_selected", locale="en", count=1)
        many = translator.t("admin.items_selected", locale="en", count=3)
        assert one == "1 item selected"
        assert many == "3 items selected"
