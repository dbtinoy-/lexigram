"""Optimistic-concurrency revision tokens for settings forms.

A rendered settings form embeds a ``settings_revision`` token derived from
the values it was rendered from. On save the submitted token is compared
against the current stored values, so a form rendered against stale state
is rejected instead of silently overwriting a newer save.

The token is **mandatory** on writes. A submission that omits it is treated
as a conflict rather than as an unguarded write — otherwise any client that
simply drops the field would bypass concurrency control entirely.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from lexigram.admin.settings.panel import SecretNode
from lexigram.serialization import dumps_str

__all__ = [
    "REVISION_FIELD",
    "extract_submitted_revision",
    "revision_matches",
    "settings_revision",
]

#: Hidden form field carrying the rendered revision token.
REVISION_FIELD = "settings_revision"


def settings_revision(spec: type[Any], values: dict[str, Any]) -> str:
    """Return a non-reversible revision token for the rendered settings.

    Args:
        spec: The config spec whose nodes define the token's field order.
        values: The values the form was rendered from.

    Returns:
        A hex SHA-256 digest over the spec's ``(key, value)`` pairs. Secret
        nodes contribute only their presence — hashing secret content would
        still create an unnecessary secret-derived identifier.
    """
    revision_values: list[tuple[str, Any]] = []
    for key, node in sorted(spec.get_nodes().items()):
        value = values.get(key)
        if isinstance(node, SecretNode):
            value = "<set>" if value else "<unset>"
        revision_values.append((key, value))
    payload = dumps_str(revision_values, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def revision_matches(
    expected: str | None,
    spec: type[Any],
    values: dict[str, Any],
) -> bool:
    """Report whether *expected* matches the current rendered revision.

    A missing or empty token never matches. Callers must render a token into
    every editable form so that legitimate submissions always carry one.

    Args:
        expected: The token submitted with the form, if any.
        spec: The config spec being saved.
        values: The current stored values to compare against.

    Returns:
        ``True`` only when a token was submitted and matches the current
        state. The comparison uses :func:`hmac.compare_digest` to avoid
        leaking match progress through timing.
    """
    if not expected:
        return False
    return hmac.compare_digest(expected, settings_revision(spec, values))


def extract_submitted_revision(form: Any) -> str | None:
    """Read the revision token from submitted form data.

    Handles both ``FormData``-style mappings and duplicate-preserving forms
    exposing ``multi_items()``. Browsers can submit a field more than once;
    the last occurrence wins, matching how the rest of the settings pipeline
    resolves duplicates.

    Args:
        form: Submitted form data.

    Returns:
        The submitted token, or ``None`` when the field is absent or blank.
    """
    multi = getattr(form, "multi_items", None)
    if callable(multi):
        submitted = [value for key, value in multi() if key == REVISION_FIELD and value]
        return str(submitted[-1]) if submitted else None

    getter = getattr(form, "get", None)
    if callable(getter):
        value = getter(REVISION_FIELD)
        return str(value) if value else None

    return None
