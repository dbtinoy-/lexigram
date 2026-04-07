"""Translation engine — Translator class, helper functions, and base catalog."""

from __future__ import annotations

import re
from typing import Any

from lexigram.logging import get_logger

logger = get_logger(__name__)

_PLURAL_SEP = "|"


def _interpolate(template: str, **kwargs: Any) -> str:
    """Replace ``{key}`` placeholders in *template* with *kwargs* values."""
    for k, v in kwargs.items():
        template = template.replace(f"{{{k}}}", str(v))
    return template


def _plural_form(value: str, count: int) -> str:
    """Select the correct plural form from a pipe-separated string.

    Supports exactly two forms: singular|plural.  If the translation has only
    one form it is always returned regardless of count.

    Args:
        value: Raw translation value, e.g. ``"{count} item|{count} items"``.
        count: The count used for plural selection.

    Returns:
        The selected form (singular if count == 1, plural otherwise).
    """
    parts = value.split(_PLURAL_SEP, maxsplit=1)
    if len(parts) == 1:
        return parts[0]
    return parts[0] if count == 1 else parts[1]


def _parse_accept_language(header: str) -> list[str]:
    """Parse ``Accept-Language`` header into an ordered locale list.

    Args:
        header: Raw ``Accept-Language`` header value.

    Returns:
        Locale codes ordered by quality value (highest first).
    """
    locales: list[tuple[float, str]] = []
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"([a-zA-Z\-]+)(?:;q=([0-9.]+))?", part)
        if m:
            tag = m.group(1).replace("_", "-")
            q = float(m.group(2)) if m.group(2) else 1.0
            locales.append((q, tag))
    locales.sort(key=lambda x: x[0], reverse=True)
    return [tag for _, tag in locales]


class Translator:
    """Manages translation catalogs and resolves translations.

    Args:
        default_locale: Locale used when no specific locale is given.
            Defaults to ``"en"``.
    """

    def __init__(self, default_locale: str = "en") -> None:
        self._catalogs: dict[str, dict[str, str]] = {}
        self._default_locale = default_locale

    # ------------------------------------------------------------------
    # Catalog management
    # ------------------------------------------------------------------

    def load_catalog(self, locale: str, catalog: dict[str, str]) -> None:
        """Merge *catalog* into the existing translations for *locale*.

        Keys are dot-notation strings; values are translation strings with
        optional pipe-separated plural forms and ``{placeholder}`` tokens.

        Args:
            locale: BCP 47 locale tag (e.g. ``"en"``, ``"fr-CA"``).
            catalog: Mapping of translation keys to values.
        """
        existing = self._catalogs.setdefault(locale, {})
        existing.update(catalog)
        logger.debug("Loaded %d translation keys for locale '%s'", len(catalog), locale)

    def get_catalog(self, locale: str) -> dict[str, str]:
        """Return the raw catalog for a locale (empty dict if not loaded).

        Args:
            locale: BCP 47 locale tag.
        """
        return dict(self._catalogs.get(locale, {}))

    @property
    def loaded_locales(self) -> list[str]:
        """Sorted list of locale codes that have catalogs loaded."""
        return sorted(self._catalogs)

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    def _fallback_chain(self, locale: str) -> list[str]:
        """Build the fallback chain for a locale.

        ``fr-CA`` → ``fr-CA``, ``fr``, ``<default>``.

        Args:
            locale: Starting locale.
        """
        chain: list[str] = [locale]
        if "-" in locale:
            chain.append(locale.split("-", maxsplit=1)[0])
        if self._default_locale not in chain:
            chain.append(self._default_locale)
        return chain

    def t(
        self,
        key: str,
        *,
        locale: str | None = None,
        count: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Translate *key* to the given locale.

        Args:
            key: Dot-notation translation key.
            locale: Target locale.  Falls back through the fallback chain to
                the default locale.
            count: When provided, plural form selection is performed before
                interpolation.  Also added to interpolation kwargs as
                ``count``.
            **kwargs: Named placeholders substituted into the translation.

        Returns:
            Translated string.  If no translation is found, *key* is returned
            as-is (last-resort fallback) and a warning is logged.
        """
        resolved_locale = locale or self._default_locale
        chain = self._fallback_chain(resolved_locale)

        raw: str | None = None
        for candidate in chain:
            catalog = self._catalogs.get(candidate, {})
            if key in catalog:
                raw = catalog[key]
                break

        if raw is None:
            logger.warning(
                "Missing translation key '%s' for locale '%s'", key, resolved_locale
            )
            raw = key

        if count is not None:
            raw = _plural_form(raw, count)
            kwargs.setdefault("count", count)

        if kwargs:
            raw = _interpolate(raw, **kwargs)

        return raw

    # Shorthand
    __call__ = t

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def format_number(
        value: float, *, _locale: str = "en", decimals: int | None = None
    ) -> str:
        """Format *value* as a locale-aware number string.

        Args:
            value: Numeric value to format.
            locale: BCP 47 locale tag (used for grouping/decimal separator).
            decimals: Number of decimal places.  ``None`` lets Python decide.

        Returns:
            Formatted string, e.g. ``"1,234.56"`` for ``en``.
        """
        if decimals is not None:
            return f"{value:,.{decimals}f}"
        if isinstance(value, int):
            return f"{value:,}"
        return f"{value:,}"

    @staticmethod
    def format_currency(
        amount: float, currency: str = "USD", *, _locale: str = "en"
    ) -> str:
        """Format *amount* as a currency string.

        Args:
            amount: Monetary amount.
            currency: ISO 4217 currency code (e.g. ``"USD"``, ``"EUR"``).
            locale: BCP 47 locale tag (reserved for future locale-aware impl).

        Returns:
            Formatted string, e.g. ``"$1,234.56"`` for USD.
        """
        symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
        symbol = symbols.get(currency.upper(), currency)
        formatted = f"{amount:,.2f}"
        return f"{symbol}{formatted}"

    @staticmethod
    def format_date(dt: Any, *, fmt: str = "%Y-%m-%d", _locale: str = "en") -> str:
        """Format a date/datetime object.

        Args:
            dt: A ``datetime.date`` or ``datetime.datetime`` instance.
            fmt: ``strftime`` format string.
            locale: Reserved for future locale-aware formatting.

        Returns:
            Formatted date string.
        """
        return dt.strftime(fmt)

    @staticmethod
    def format_datetime(
        dt: Any,
        *,
        fmt: str = "%Y-%m-%d %H:%M",
        timezone: str | None = None,
        _locale: str = "en",
    ) -> str:
        """Format a datetime, optionally converting to a target timezone.

        Args:
            dt: A ``datetime.datetime`` instance.
            fmt: ``strftime`` format string.
            timezone: IANA timezone name (e.g. ``"America/New_York"``).
                      If ``None``, no conversion is performed.
            locale: Reserved for future locale-aware formatting.

        Returns:
            Formatted datetime string in the target timezone.
        """
        from datetime import datetime as _datetime
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        if timezone and isinstance(dt, _datetime):
            try:
                tz = ZoneInfo(timezone)
                dt = dt.astimezone(tz)
            except (ZoneInfoNotFoundError, ValueError, AttributeError):
                pass
        return dt.strftime(fmt)


_BASE_EN: dict[str, str] = {
    "admin.save": "Save",
    "admin.cancel": "Cancel",
    "admin.delete": "Delete",
    "admin.restore": "Restore",
    "admin.edit": "Edit",
    "admin.create": "Create",
    "admin.search": "Search",
    "admin.filter": "Filter",
    "admin.export": "Export",
    "admin.import": "Import",
    "admin.back": "Back",
    "admin.confirm": "Are you sure?",
    "admin.loading": "Loading…",
    "admin.no_results": "No results found.",
    "admin.items_selected": "{count} item selected|{count} items selected",
    "admin.page_of": "Page {page} of {total}",
    "admin.error.required": "{field} is required.",
    "admin.error.not_found": "{resource} not found.",
    "admin.success.created": "{resource} created successfully.",
    "admin.success.updated": "{resource} updated successfully.",
    "admin.success.deleted": "{resource} deleted successfully.",
}

#: Module-level :class:`Translator` instance.  Pre-loaded with a minimal
#: English base catalog.  Applications should call :meth:`Translator.load_catalog`
#: at startup to extend / override translations.
translator = Translator(default_locale="en")
translator.load_catalog("en", _BASE_EN)


__all__ = [
    "Translator",
    "translator",
]
