"""Exceptions for the serialization subsystem.

Exception Hierarchy::

    LexigramError
    └── SerializationError
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.exceptions import LexigramError


class SerializationError(LexigramError):
    """Base exception for serialization and deserialization failures.

    Extensions should subclass this for domain-specific errors::

        class CacheSerializationError(SerializationError):
            ...
    """

    _code = "LEX_ERR_SERIAL_003"

    def __init__(
        self,
        message: str = "Serialization failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)


class NegotiationError(SerializationError):
    """Raised when no serializer can be negotiated for a given Accept header."""

    _code = "LEX_ERR_SERIAL_004"

    def __init__(
        self,
        accept_header: str = "",
        **kwargs: Any,
    ) -> None:
        message = (
            f"No serializer available for Accept header: {accept_header!r}"
            if accept_header
            else "No serializer registered"
        )
        super().__init__(message, **kwargs)


__all__ = ["NegotiationError", "SerializationError"]
