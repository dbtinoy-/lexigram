"""Shared naming helpers for project emitters."""

from __future__ import annotations

from lexigram.contracts.cli.generators import pascal_case, snake_case


def pluralize(name: str) -> str:
    """Naive pluralization (documented v1 behavior: user->users)."""
    if name.endswith("y") and name[-2:-1] not in {"a", "e", "i", "o", "u"}:
        return f"{name[:-1]}ies"
    if name.endswith("s"):
        return name
    return f"{name}s"


def table_name(entity_name: str) -> str:
    """Pluralized snake_case table name."""
    return pluralize(snake_case(entity_name))


def pascal_entity(name: str) -> str:
    return pascal_case(name)
