"""Data transformation utilities for the admin layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class DataTransformer:
    """Handles data preparation between storage and UI layers.

    This is used to format raw database/API data for form display
    and to process form submissions back into a serializable format.
    """

    def __init__(self) -> None:
        """Initialize with empty transform maps."""
        self._to_form: dict[str, Callable] = {}
        self._from_form: dict[str, Callable] = {}

    def register(self, field_name: str, to_form: Callable, from_form: Callable) -> None:
        """Register transform functions for a specific field."""
        self._to_form[field_name] = to_form
        self._from_form[field_name] = from_form

    def transform_to_form(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply all 'to_form' transformations to a data dictionary."""
        result = dict(data)
        for field, transformer in self._to_form.items():
            if field in result:
                result[field] = transformer(result[field])
        return result

    def transform_from_form(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply all 'from_form' transformations to a data dictionary."""
        result = dict(data)
        for field, transformer in self._from_form.items():
            if field in result:
                result[field] = transformer(result[field])
        return result


# Standard Transformers


def json_transformer() -> Any:
    """Transformer for JSON string <-> Object."""
    from lexigram.serialization import dumps_str, loads_str

    return (
        lambda x: loads_str(x) if isinstance(x, str) else x,
        lambda x: dumps_str(x) if not isinstance(x, str) else x,
    )


def comma_separated_list() -> Any:
    """Transformer for CSV String <-> List."""
    return (
        lambda x: [s.strip() for s in x.split(",")] if isinstance(x, str) else x,
        lambda x: ", ".join(x) if isinstance(x, list) else x,
    )


__all__ = ["DataTransformer", "comma_separated_list", "json_transformer"]
