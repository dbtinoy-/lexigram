"""Small URL helpers used by HTML components.

Rendering an attribute through ``Element`` escapes markup, but it does not
make an unsafe URL scheme safe. Keep navigation scheme validation in one
place so components consistently refuse ``javascript:``, ``data:``, and
other active schemes while still supporting ordinary relative asset links.
"""

from __future__ import annotations

from urllib.parse import urlsplit

_ALLOWED_NETWORK_SCHEMES = frozenset({"http", "https"})


def is_safe_navigation_url(value: str | None) -> bool:
    """Return whether ``value`` is safe to use as an ``href`` or ``src``.

    Absolute network URLs must use HTTP(S). Relative paths are allowed for
    application-local links and assets. Protocol-relative URLs (``//host``)
    and malformed scheme-bearing values are rejected because they can move a
    browser to an untrusted origin without an explicit allowed scheme.
    Control characters are rejected before parsing because browsers normalize
    them in ways that can change the interpreted scheme.
    """
    if not isinstance(value, str):
        return False
    candidate = value.strip()
    if not candidate or any(ord(char) < 0x20 for char in candidate):
        return False

    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return False

    if parsed.scheme:
        return parsed.scheme.lower() in _ALLOWED_NETWORK_SCHEMES and bool(
            parsed.netloc
        )
    if parsed.netloc:
        # ``//example.test/path`` is protocol-relative and therefore not a
        # local relative path.
        return False
    return True


__all__ = ["is_safe_navigation_url"]
