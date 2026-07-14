"""NoSQL filter validation against operator and identifier injection.

Ports the sibling-package allowlist/identifier-validation primitive
(``lexigram-graph``'s ``_SAFE_CYPHER_RE``/``_validate_ident`` and
``lexigram-search``'s ``_validate_field_name``) into a shared validator
applied at every driver boundary and fluent-API edge of this package.
"""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from lexigram.nosql.exceptions import NoSQLFilterError

_SAFE_IDENT_RE = re.compile(r"^[a-zA-Z0-9._-]+$")

_TOP_LEVEL_ALLOWED = frozenset({"$and", "$or", "$nor", "$not", "$text"})

_NESTED_ALLOWED = frozenset(
    {
        "$eq",
        "$ne",
        "$gt",
        "$gte",
        "$lt",
        "$lte",
        "$in",
        "$nin",
        "$exists",
        "$type",
        "$all",
        "$elemMatch",
        "$size",
        "$text",
        "$regex",
    },
)

_DENIED_ANY_POSITION = frozenset(
    {"$where", "$expr", "$mod", "$function", "$accumulator"},
)

_PIPELINE_WRITE_STAGES = frozenset({"$merge", "$out"})

_TEXT_LANGUAGES = frozenset(
    {
        "english",
        "spanish",
        "french",
        "german",
        "portuguese",
        "italian",
        "dutch",
        "russian",
        "arabic",
        "chinese",
        "chineseTraditional",
        "japanese",
        "korean",
    },
)

_MAX_REGEX_LENGTH = 1024
_REGEX_OPTIONS = frozenset("imxsu")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
_TEXT_QUERY_KEYS = frozenset({"$search", "$language"})


def validate_filter(filter: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate a MongoDB-style filter dict.

    Applies the operator allowlists (top-level vs nested position) and
    the identifier pattern to every plain field key. ``$where``,
    ``$expr``, ``$mod``, ``$function`` and ``$accumulator`` are denied in
    any position; ``$regex`` is permitted only when the shared shape gate
    passes; ``$text`` is shape-checked.

    Args:
        filter: The filter dict, as passed to a driver boundary.

    Returns:
        The validated filter, unchanged.

    Raises:
        NoSQLFilterError: If the filter contains a denied or misplaced
            operator, an unsafe field name, or a malformed ``$text`` /
            ``$regex`` shape.
    """
    _scan_denied(filter)
    _validate_query_dict(filter)
    return filter


def validate_field_name(field: str) -> None:
    """Validate a filter field name.

    Rejects ``$``-prefixed names (operators must go through dedicated
    operators) and any name outside alphanumeric, underscore, dash,
    and dot characters.

    Args:
        field: Field name to validate.

    Raises:
        NoSQLFilterError: If the name is unsafe.
    """
    if not _SAFE_IDENT_RE.match(field):
        raise NoSQLFilterError(
            f"Invalid field name: {field!r}. "
            "Only alphanumeric, underscore, dash, and dot allowed.",
        )


def _regex_shape_ok(pattern: Any, options: Any) -> bool:
    """Shared regex shape gate: pattern and options are safe to inline.

    Args:
        pattern: The regex pattern value.
        options: The ``$options`` companion value.

    Returns:
        ``True`` when the pattern is a non-empty, length-capped,
        single-line string without control characters or semicolons,
        and the options are a subset of ``i``/``m``/``x``/``s``/``u``.
    """
    if not isinstance(pattern, str) or not pattern:
        return False
    if len(pattern) > _MAX_REGEX_LENGTH:
        return False
    if ";" in pattern or _CONTROL_CHARS_RE.search(pattern):
        return False
    if not isinstance(options, str):
        return False
    return not set(options) - _REGEX_OPTIONS


def _scan_denied(value: Any) -> None:
    """Reject evaluation operators in any position, recursively."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in _DENIED_ANY_POSITION:
                raise NoSQLFilterError(f"Operator {key!r} is denied in filters")
            _scan_denied(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _scan_denied(item)


def _validate_query_dict(filter: Mapping[str, Any]) -> None:
    if not isinstance(filter, Mapping):
        raise NoSQLFilterError(
            f"Filter must be a mapping, got {type(filter).__name__}",
        )
    for key, value in filter.items():
        _validate_query_key(key, value)


def _validate_query_key(key: Any, value: Any) -> None:
    if not isinstance(key, str):
        raise NoSQLFilterError(
            f"Filter keys must be strings, got {type(key).__name__}",
        )
    if key in _DENIED_ANY_POSITION:
        raise NoSQLFilterError(f"Operator {key!r} is denied in filters")
    if key.startswith("$"):
        if key not in _TOP_LEVEL_ALLOWED:
            raise NoSQLFilterError(
                f"Operator {key!r} is not allowed in this position",
            )
        if key in {"$and", "$or", "$nor"}:
            if not isinstance(value, list):
                raise NoSQLFilterError(
                    f"Operator {key!r} requires a list of filter dicts",
                )
            for condition in value:
                _validate_query_dict(condition)
        elif key == "$text":
            _validate_text_query(value)
        elif key == "$not":
            if not isinstance(value, Mapping):
                raise NoSQLFilterError("Operator '$not' requires a dict")
            _validate_operator_dict(value)
    else:
        validate_field_name(key)
        _validate_field_value(value)


def _validate_field_value(value: Any) -> None:
    """Validate the value of a plain field key (literal or operator dict)."""
    if not isinstance(value, Mapping):
        return
    for key, item in value.items():
        if not isinstance(key, str):
            raise NoSQLFilterError(
                f"Filter keys must be strings, got {type(key).__name__}",
            )
        if key in _DENIED_ANY_POSITION:
            raise NoSQLFilterError(f"Operator {key!r} is denied in filters")
        if key == "$options":
            if "$regex" not in value:
                raise NoSQLFilterError(
                    "Operator '$options' is only allowed alongside '$regex'",
                )
            continue
        if key.startswith("$"):
            if key not in _NESTED_ALLOWED:
                raise NoSQLFilterError(
                    f"Operator {key!r} is not allowed in this position",
                )
            _validate_operator(key, item, value)
        else:
            _validate_field_value(item)


def _validate_operator(
    key: str,
    value: Any,
    owner: Mapping[str, Any],
) -> None:
    """Validate a nested operator and its operand shapes."""
    if key == "$regex":
        if not _regex_shape_ok(value, owner.get("$options", "")):
            raise NoSQLFilterError("Invalid $regex pattern or options")
    elif key == "$text":
        _validate_text_query(value)
    elif key == "$elemMatch" and isinstance(value, Mapping):
        _validate_field_value(value)


def _validate_operator_dict(operators: Mapping[str, Any]) -> None:
    """Validate a bare operator dict (e.g. the value of ``$not``)."""
    for key, value in operators.items():
        if not isinstance(key, str):
            raise NoSQLFilterError(
                f"Operator keys must be strings, got {type(key).__name__}",
            )
        if key in _DENIED_ANY_POSITION:
            raise NoSQLFilterError(f"Operator {key!r} is denied in filters")
        if key == "$options":
            if "$regex" not in operators:
                raise NoSQLFilterError(
                    "Operator '$options' is only allowed alongside '$regex'",
                )
            continue
        if key.startswith("$"):
            if key in {"$and", "$or", "$nor"}:
                if not isinstance(value, list):
                    raise NoSQLFilterError(
                        f"Operator {key!r} requires a list of filter dicts",
                    )
                for condition in value:
                    _validate_query_dict(condition)
            elif key == "$text":
                _validate_text_query(value)
            elif key == "$not":
                if not isinstance(value, Mapping):
                    raise NoSQLFilterError("Operator '$not' requires a dict")
                _validate_operator_dict(value)
            else:
                if key not in _NESTED_ALLOWED:
                    raise NoSQLFilterError(
                        f"Operator {key!r} is not allowed in this position",
                    )
                _validate_operator(key, value, operators)
        else:
            raise NoSQLFilterError(
                f"Unexpected field key {key!r} in operator dict",
            )


def _validate_text_query(value: Any) -> None:
    """Validate the ``$text`` query shape ($search string, $language allowlist)."""
    if not isinstance(value, Mapping):
        raise NoSQLFilterError("Operator '$text' requires a dict")
    if not set(value) <= _TEXT_QUERY_KEYS:
        raise NoSQLFilterError(
            "Operator '$text' allows only '$search' and '$language'",
        )
    search = value.get("$search")
    if not isinstance(search, str) or not search:
        raise NoSQLFilterError(
            "Operator '$text' requires a non-empty string '$search'",
        )
    language = value.get("$language")
    if language is not None and language not in _TEXT_LANGUAGES:
        raise NoSQLFilterError(f"Unsupported $text language: {language!r}")
