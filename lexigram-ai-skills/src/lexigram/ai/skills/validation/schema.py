"""JSON Schema parameter validation for skills."""

from __future__ import annotations

from typing import Any


def validate_params(params: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Validate *params* against a JSON Schema ``object`` descriptor.

    Supports: required fields, type checking, enum, minimum/maximum,
    minLength/maxLength, and nested object/array types.

    Args:
        params: The parameter dict supplied by the caller.
        schema: JSON Schema ``object`` definition from SkillDefinition.

    Returns:
        List of validation error messages.  Empty list means valid.
    """
    if not schema:
        return []

    errors: list[str] = []
    properties: dict[str, Any] = schema.get("properties", {})
    required: list[str] = schema.get("required", [])

    for name in required:
        if name not in params or params[name] is None:
            errors.append(f"'{name}' is required")

    for name, value in params.items():
        if name not in properties:
            continue
        prop = properties[name]
        errors.extend(_validate_property(name, value, prop))

    return errors


def _validate_property(name: str, value: Any, prop: dict[str, Any]) -> list[str]:
    """Validate a single parameter against its property schema.

    Args:
        name: Parameter name (for error messages).
        value: The supplied value.
        prop: JSON Schema property descriptor.

    Returns:
        List of validation error strings.
    """
    errors: list[str] = []
    expected_type = prop.get("type")

    if expected_type and value is not None:
        if not _check_type(value, expected_type):
            errors.append(
                f"'{name}' must be of type {expected_type!r}, got {type(value).__name__!r}"
            )
            return errors  # skip further checks if type is wrong

    if "enum" in prop and value not in prop["enum"]:
        errors.append(f"'{name}' must be one of {prop['enum']}")

    if expected_type in ("integer", "number") and value is not None:
        if "minimum" in prop and value < prop["minimum"]:
            errors.append(f"'{name}' must be >= {prop['minimum']}")
        if "maximum" in prop and value > prop["maximum"]:
            errors.append(f"'{name}' must be <= {prop['maximum']}")

    if expected_type == "string" and value is not None:
        if "minLength" in prop and len(value) < prop["minLength"]:
            errors.append(f"'{name}' must have length >= {prop['minLength']}")
        if "maxLength" in prop and len(value) > prop["maxLength"]:
            errors.append(f"'{name}' must have length <= {prop['maxLength']}")

    return errors


_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}


def _check_type(value: Any, expected: str) -> bool:
    """Return True if *value* matches the JSON Schema *expected* type.

    Args:
        value: Value to check.
        expected: JSON Schema type string.

    Returns:
        True if the type matches.
    """
    py_type = _TYPE_MAP.get(expected)
    if py_type is None:
        return True  # Unknown type — allow
    # Booleans are ints in Python; disallow bool for integer/number
    if expected in ("integer", "number") and isinstance(value, bool):
        return False
    return isinstance(value, py_type)
