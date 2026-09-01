"""Canonical construction of ``?next=`` login redirect URLs.

Every unauthenticated redirect in the admin panel sends the user to the
login page carrying the path they originally asked for. Those URLs were
previously built with ad-hoc f-strings in nine places, split between
``quote_plus`` (which percent-encodes ``/`` as ``%2F``) and
``quote(path, safe="/")`` (which does not). Both decode to the same value,
so neither was unsafe, but the encoded form leaks into the address bar and
into audit logs as ``%2Fadmin%2Fprofile%2Fmfa``.

This module is the single place that decides how a ``next`` parameter is
encoded, so the rendered URL is identical no matter which layer issues the
redirect.
"""

from __future__ import annotations

from urllib.parse import quote, urlencode

__all__ = [
    "build_login_redirect",
    "encode_next_value",
]


def encode_next_value(path: str) -> str:
    """Percent-encode a return path for use as a ``next`` query value.

    Path separators are preserved so the resulting URL stays readable:
    ``/admin/profile/mfa`` rather than ``%2Fadmin%2Fprofile%2Fmfa``. Every
    other reserved character (including ``?``, ``&``, ``#`` and spaces) is
    still escaped, so a crafted path cannot inject extra query parameters.

    Args:
        path: The absolute return path, e.g. ``/admin/profile/mfa``.

    Returns:
        The encoded value, safe to interpolate after ``next=``.
    """
    return quote(path, safe="/")


def build_login_redirect(
    login_url: str,
    next_path: str | None = None,
    error: str | None = None,
    **extra: str,
) -> str:
    """Build a login URL carrying an optional return path and error message.

    Args:
        login_url: The mounted login path, e.g. ``/backoffice/login``.
        next_path: Optional path to return to after authenticating. Omitted
            from the result when falsy.
        error: Optional user-facing error message to surface on the login
            page. Omitted when falsy.
        **extra: Additional query parameters, appended in the order given.

    Returns:
        The fully-formed login URL. Parameter order is stable
        (``error``, then ``next``, then extras) so tests and audit log
        assertions do not depend on dict iteration order.
    """
    params: list[tuple[str, str]] = []
    if error:
        params.append(("error", error))
    if next_path:
        params.append(("next", next_path))
    params.extend(extra.items())

    if not params:
        return login_url

    # quote_via keeps path separators literal in the `next` value while
    # still escaping everything else; urlencode handles the rest.
    query = urlencode(params, quote_via=quote, safe="/")
    return f"{login_url}?{query}"
