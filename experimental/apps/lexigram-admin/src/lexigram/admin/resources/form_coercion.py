"""Form-data coercion and validation-error helpers for admin resources."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from decimal import InvalidOperation as DecimalInvalidOp
from enum import Enum
import types
from typing import Any, Union, cast, get_args, get_origin, get_type_hints
from uuid import UUID


def _unwrap_optional(tp: type) -> type:
    """Unwrap Optional[T] or T | None to T."""
    origin = get_origin(tp)
    if origin in (Union, types.UnionType):
        non_none = [a for a in get_args(tp) if a is not type(None)]
        if len(non_none) == 1:
            return cast("type", non_none[0])
    return tp


def _coerce_form_data(data: dict, model: type | None) -> dict:
    """Convert HTML form string values to proper Python types."""
    if model is None:
        return data
    try:
        hints = get_type_hints(model)
    except Exception:
        return data

    for key, value in list(data.items()):
        if key not in hints:
            continue

        expected = _unwrap_optional(hints[key])
        origin = get_origin(expected)

        # Multi-select and has-many controls submit repeated values. Preserve
        # and coerce every value instead of dropping the list because it is not
        # a scalar string.
        if origin is list:
            if isinstance(value, (list, tuple)):
                items = list(value)
            elif value == "":
                items = []
            elif isinstance(value, str):
                items = [s.strip() for s in value.split(",") if s.strip()]
            else:
                continue
            args = get_args(expected)
            inner = args[0] if args else str
            if inner is str:
                data[key] = [str(item) for item in items]
            else:
                try:
                    data[key] = [inner(item) for item in items]
                except (ValueError, TypeError):
                    pass
            continue

        if not isinstance(value, str):
            continue

        if expected is bool:
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                data[key] = True
            elif normalized in {"false", "0", "no", "off"}:
                data[key] = False
            elif normalized == "":
                # Keep an empty optional value nullable. A non-optional model
                # will report the missing/invalid value instead of silently
                # turning an arbitrary empty input into False.
                data[key] = None
        elif expected is int:
            try:
                data[key] = int(value)
            except (ValueError, TypeError):
                pass
        elif expected is float:
            if value == "":
                data[key] = None
            else:
                try:
                    data[key] = float(value)
                except (ValueError, TypeError):
                    pass
        elif expected is Decimal:
            if value == "":
                data[key] = None
            else:
                try:
                    data[key] = Decimal(value)
                except (DecimalInvalidOp, ValueError, TypeError):
                    pass
        elif expected is UUID:
            if value == "":
                data[key] = None
            else:
                try:
                    data[key] = UUID(value)
                except (ValueError, AttributeError):
                    pass
        elif expected is datetime:
            if value == "":
                data[key] = None
            else:
                try:
                    data[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
        elif expected is date:
            if value == "":
                data[key] = None
            else:
                try:
                    data[key] = date.fromisoformat(value)
                except (ValueError, TypeError):
                    pass
        elif isinstance(expected, type) and issubclass(expected, Enum):
            if value != "":
                try:
                    data[key] = expected(value)
                except (ValueError, TypeError):
                    pass
        elif origin is dict:
            if value != "":
                try:
                    from lexigram.serialization import loads_str as _json_loads

                    data[key] = _json_loads(value)
                except Exception:  # noqa: S110 — intentional best-effort fallback
                    pass

    return data


def _validation_errors_to_dict(error: Any) -> dict[str, list[str]]:
    """Convert AdminValidationError.errors (list[FieldError]) to dict form."""
    errors: dict[str, list[str]] = {}
    for fe in error.errors:
        errors.setdefault(fe.field, []).append(fe.message)
    return errors


__all__ = [
    "_coerce_form_data",
    "_unwrap_optional",
    "_validation_errors_to_dict",
]
