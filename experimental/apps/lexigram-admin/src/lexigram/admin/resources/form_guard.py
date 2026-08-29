"""Defense-in-depth form guard for admin resources.

Centralizes mass-assignment protection: unknown keys and protected columns
are stripped from HTML form data before it can reach a data source. This is
the single source of truth used by both the live handler pipeline
(``Resource.before_validate``) and the legacy ``ResourceController``
validation helpers.

Rules
-----
- Protected columns (``id``, ``tenant_id``, ``created_at``, ``updated_at``)
  are **always** dropped — they are framework-managed and must never be
  client-settable.
- When a model is bound and ``allow_extra_fields`` is False (the default),
  unknown keys are dropped as well (mass-assignment protection).
- Values are coerced to the model's declared Python types (HTML form
  strings → bool/int/float/date/datetime/...).
- The input mapping is never mutated; a new dict is returned.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Final

from lexigram.admin.resources.form_coercion import _coerce_form_data

#: Columns that are framework-managed and never client-settable.
PROTECTED_FORM_FIELDS: Final[frozenset[str]] = frozenset(
    {"id", "tenant_id", "created_at", "updated_at"}
)


def model_field_names(model: type | None) -> set[str]:
    """Return the set of declared, writable model field names.

    ``ClassVar`` annotations and private (underscore-prefixed) members are
    excluded. Returns an empty set when no model is bound.
    """
    if model is None:
        return set()
    fields = getattr(model, "model_fields", None) or getattr(
        model, "__annotations__", {}
    )
    allowed: set[str] = set()
    for key, ann in fields.items():
        if key.startswith("_") or str(ann).startswith("ClassVar"):
            continue
        allowed.add(key)
    return allowed


def sanitize_form_data(
    data: Mapping[str, Any],
    *,
    model: type | None,
    protected_fields: Iterable[str] = PROTECTED_FORM_FIELDS,
    allow_extra_fields: bool = False,
) -> dict[str, Any]:
    """Coerce and strip untrusted HTML form data.

    Args:
        data: Raw form data (multipart form, query params, …).
        model: Optional domain model type used to coerce values and to
            whitelist writable fields. When ``None`` only protected columns
            are dropped (unknown keys pass through for untyped resources).
        protected_fields: Columns that are never client-settable.
        allow_extra_fields: When True, unknown keys are kept (protected
            columns are still dropped). Use sparingly — e.g. resources that
            shadow extra form-only fields.

    Returns:
        A new dict with coerced values and unauthorized keys removed.
    """
    protected = frozenset(protected_fields)
    cleaned = dict(data)

    if model is not None:
        cleaned = _coerce_form_data(cleaned, model)
        if not allow_extra_fields:
            allowed = model_field_names(model) - protected
            return {key: value for key, value in cleaned.items() if key in allowed}

    # Untyped resources (or opt-in allow_extra_fields): drop protected keys
    # only — bare passthrough would let clients set tenant_id / id.
    return {key: value for key, value in cleaned.items() if key not in protected}


__all__ = ["PROTECTED_FORM_FIELDS", "model_field_names", "sanitize_form_data"]
