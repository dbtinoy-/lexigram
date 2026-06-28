"""One RoleDefinition — auth re-exports contracts (AGENTS.md §2.6)."""

from __future__ import annotations

from lexigram.auth.types import RoleDefinition
from lexigram.contracts.auth import RoleDefinition as ContractsRole


def test_single_definition() -> None:
    assert RoleDefinition is ContractsRole
    assert RoleDefinition(name="x").permissions == []