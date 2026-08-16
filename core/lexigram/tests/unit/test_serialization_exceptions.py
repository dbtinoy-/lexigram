"""Unit tests for serialization exceptions."""

import pytest

from lexigram.serialization.exceptions import (
    NegotiationError,
    SerializationError,
)


class TestSerializationError:
    def test_inheritance(self) -> None:
        assert issubclass(SerializationError, Exception)

    def test_code(self) -> None:
        assert SerializationError._code == "LEX_ERR_SERIAL_003"

    def test_default_message(self) -> None:
        exc = SerializationError()
        assert "Serialization failed" in str(exc)


class TestNegotiationError:
    def test_inheritance(self) -> None:
        assert issubclass(NegotiationError, SerializationError)

    def test_code(self) -> None:
        assert NegotiationError._code == "LEX_ERR_SERIAL_004"

    def test_accept_header_message(self) -> None:
        exc = NegotiationError(accept_header="application/json")
        assert "application/json" in str(exc)

    def test_no_accept_header_message(self) -> None:
        exc = NegotiationError()
        assert "No serializer registered" in str(exc)