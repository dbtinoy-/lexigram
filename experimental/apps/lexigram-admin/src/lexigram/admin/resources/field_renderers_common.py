"""Shared protocol and arg builder for field renderers."""

from __future__ import annotations

from typing import Any, Protocol

from lexigram.admin.schema import SchemaField


class FieldRendererProtocol(Protocol):
    """Protocol for field renderers."""

    def can_render(self, field_schema: SchemaField) -> bool: ...

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any: ...


def _atom_args(
    common_args: dict[str, Any], value: Any, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build atom kwargs from shared inline-editing args.

    Args:
        common_args: Shared args (name, label, required, disabled, hx_*, ...).
        value: Current field value.
        extra: Additional atom-specific kwargs.

    Returns:
        Kwargs acceptable by lexigram.ui input atoms.
    """
    args: dict[str, Any] = {
        "name": common_args["name"],
        "value": value if value is not None else "",
        "label": common_args.get("label"),
        "required": common_args.get("required", False),
        "disabled": common_args.get("disabled", False),
    }
    for key in ("placeholder", "error"):
        if common_args.get(key):
            args[key] = common_args[key]
    args.update({k: v for k, v in common_args.items() if k.startswith("hx_")})
    if extra:
        args.update(extra)
    return args
