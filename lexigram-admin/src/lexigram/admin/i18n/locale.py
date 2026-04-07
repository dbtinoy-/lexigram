"""Locale and timezone resolution helpers for per-request i18n."""

from __future__ import annotations

from typing import Any

from lexigram.admin.i18n.translator import _parse_accept_language

_LOCALE_COOKIE = "admin_locale"
_LOCALE_HEADER = "accept-language"


def convert_to_timezone(dt: Any, timezone: str) -> Any:
    """Convert *dt* to the given IANA *timezone*.

    Args:
        dt: A timezone-aware ``datetime.datetime`` instance.
        timezone: IANA timezone name (e.g. ``"Europe/Paris"``).

    Returns:
        The datetime shifted into *timezone*, or *dt* unchanged if conversion
        fails.
    """
    from datetime import datetime as _datetime
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    if not isinstance(dt, _datetime):
        return dt
    try:
        return dt.astimezone(ZoneInfo(timezone))
    except (ZoneInfoNotFoundError, ValueError, AttributeError):
        return dt


def get_user_timezone(request: Any, *, default: str = "UTC") -> str:
    """Resolve the user's preferred timezone from a request.

    Resolution order:
    1. ``request.state.timezone`` (set by middleware or profile)
    2. Cookie named ``admin_timezone``
    3. *default* (``"UTC"``)

    Args:
        request: Starlette-compatible request object.
        default: Fallback timezone name.

    Returns:
        IANA timezone string.
    """
    state_tz = getattr(getattr(request, "state", None), "timezone", None)
    if state_tz:
        return str(state_tz)

    cookies = getattr(request, "cookies", {})
    if isinstance(cookies, dict) and "admin_timezone" in cookies:
        return cookies["admin_timezone"]

    return default


def get_locale(
    request: Any,
    *,
    default: str = "en",
    cookie_name: str = _LOCALE_COOKIE,
) -> str:
    """Resolve the best locale for a request.

    Resolution order:
    1. ``request.state.locale`` (set by middleware or login flow)
    2. Cookie named *cookie_name*
    3. ``Accept-Language`` header (first match)
    4. *default*

    Args:
        request: Starlette-compatible request object.
        default: Fallback locale when nothing else is found.
        cookie_name: Name of the locale cookie.

    Returns:
        BCP 47 locale tag.
    """
    # 1. Explicit state override
    state_locale = getattr(getattr(request, "state", None), "locale", None)
    if state_locale:
        return str(state_locale)

    # 2. Cookie
    cookies = getattr(request, "cookies", {})
    if isinstance(cookies, dict) and cookie_name in cookies:
        return cookies[cookie_name]

    # 3. Accept-Language header
    headers = getattr(request, "headers", {})
    accept = (
        headers.get(_LOCALE_HEADER, "")
        if isinstance(headers, dict)
        else getattr(headers, "get", lambda _k, d="": d)(_LOCALE_HEADER, "")
    )
    if accept:
        locales = _parse_accept_language(accept)
        if locales:
            return locales[0]

    return default


__all__ = [
    "convert_to_timezone",
    "get_locale",
    "get_user_timezone",
]
