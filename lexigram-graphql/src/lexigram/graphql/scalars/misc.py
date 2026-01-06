from __future__ import annotations

from typing import Any
import uuid


class UUID:
    """Custom scalar for UUID values."""

    @staticmethod
    def serialize(uid: uuid.UUID | None) -> str | None:
        if uid is None:
            return None
        if isinstance(uid, uuid.UUID):
            return str(uid)
        raise ValueError(f"Cannot serialize {type(uid)} as UUID")

    @staticmethod
    def parse_value(value: str | None) -> uuid.UUID | None:
        if value is None:
            return None
        return uuid.UUID(value)


class Email:
    """Custom scalar for email values."""

    @staticmethod
    def serialize(email: str | None) -> str | None:
        if email is None:
            return None
        if isinstance(email, str) and "@" in email:
            return email.lower()
        raise ValueError(f"Cannot serialize {type(email)} as Email")

    @staticmethod
    def parse_value(value: str | None) -> str | None:
        if value is None:
            return None
        return value.lower()


class URL:
    """Custom scalar for URL values."""

    @staticmethod
    def serialize(url: str | None) -> str | None:
        if url is None:
            return None
        if isinstance(url, str):
            return url
        raise ValueError(f"Cannot serialize {type(url)} as URL")

    @staticmethod
    def parse_value(value: str | None) -> str | None:
        if value is None:
            return None
        return value


class BigInt:
    """Custom scalar for big integer values."""

    @staticmethod
    def serialize(value: int | None) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def parse_value(value: str | None) -> int | None:
        if value is None:
            return None
        return int(value)


class Void:
    """Custom scalar for void/null values."""

    @staticmethod
    def serialize(_value: Any) -> None:
        return

    @staticmethod
    def parse_value(_value: Any) -> None:
        return


__all__ = [
    "URL",
    "UUID",
    "BigInt",
    "Email",
    "Void",
]
