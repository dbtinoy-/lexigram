"""Tests for AdminObjectMapper and admin mapping registrations.

Covers:
- AdminObjectMapper.register / map
- register_admin_mappings
- mapping __init__ re-exports
"""

from __future__ import annotations

import pytest

from lexigram.admin.auth.entity import AdminUserEntity
from lexigram.admin.auth.user import AdminUserRecord
from lexigram.admin.mapping import AdminObjectMapper, register_admin_mappings


class TestAdminObjectMapper:
    """Tests for AdminObjectMapper."""

    def test_register_and_map(self) -> None:
        mapper = AdminObjectMapper()
        mapper.add(str, int, int)
        result = mapper.map("42", int)
        assert result == 42

    def test_map_unknown_raises_key_error(self) -> None:
        mapper = AdminObjectMapper()
        with pytest.raises(KeyError):
            mapper.map("hello", int)

    def test_register_with_lambda(self) -> None:
        mapper = AdminObjectMapper()
        mapper.add(str, list, lambda s: list(s))
        result = mapper.map("abc", list)
        assert result == ["a", "b", "c"]

    def test_map_with_validate_false(self) -> None:
        mapper = AdminObjectMapper()
        mapper.add(str, int, int)
        result = mapper.map("10", int, validate=False)
        assert result == 10

    def test_map_with_validate_and_validator(self) -> None:
        called = []

        def validator(r: int) -> None:
            called.append(r)

        mapper = AdminObjectMapper()
        mapper.add(str, int, int)
        result = mapper.map("5", int, validate=True, validator=validator)
        assert result == 5
        assert called == [5]

    def test_map_with_validate_true_no_validator(self) -> None:
        mapper = AdminObjectMapper()
        mapper.add(str, int, int)
        # validate=True but no validator → just maps normally
        result = mapper.map("7", int, validate=True)
        assert result == 7

    def test_overwrite_registration(self) -> None:
        mapper = AdminObjectMapper()
        mapper.add(str, int, lambda s: 0)
        mapper.add(str, int, lambda s: 99)
        result = mapper.map("x", int)
        assert result == 99

    def test_multiple_registrations(self) -> None:
        mapper = AdminObjectMapper()
        mapper.add(str, int, int)
        mapper.add(str, list, list)
        assert mapper.map("5", int) == 5
        assert mapper.map("abc", list) == ["a", "b", "c"]


class TestRegisterAdminMappings:
    """Tests for register_admin_mappings."""

    def setup_method(self) -> None:
        self.mapper = AdminObjectMapper()
        register_admin_mappings(self.mapper)

    def test_entity_to_record(self) -> None:
        entity = AdminUserEntity(
            id="ent-1",
            username="alice",
            email="alice@example.com",
            hashed_password="pw",
            roles=["admin"],
            permissions=["read"],
            is_active=True,
            is_verified=True,
        )
        record = self.mapper.map(entity, AdminUserRecord)
        assert isinstance(record, AdminUserRecord)
        assert record.user_id == "ent-1"
        assert record.name == "alice"
        assert record.email == "alice@example.com"

    def test_entity_to_dict(self) -> None:
        entity = AdminUserEntity(
            id="ent-2",
            username="bob",
            email="bob@example.com",
            hashed_password="hash",
            roles=["editor"],
            permissions=[],
            is_active=True,
            is_verified=False,
        )
        d = self.mapper.map(entity, dict)
        assert isinstance(d, dict)
        assert d["id"] == "ent-2"
        assert d["username"] == "bob"
        assert d["email"] == "bob@example.com"
        assert d["roles"] == ["editor"]
        assert d["is_active"] is True
        assert d["is_verified"] is False
        assert d["updated_at"] is None

    def test_record_to_entity(self) -> None:
        record = AdminUserRecord(
            user_id="rec-1",
            name="carol",
            email="carol@example.com",
            hashed_password="hashed",
            roles=["viewer"],
            permissions=["view"],
            is_active=True,
            is_verified=True,
        )
        entity = self.mapper.map(record, AdminUserEntity)
        assert isinstance(entity, AdminUserEntity)
        assert entity.id == "rec-1"
        assert entity.username == "carol"

    def test_entity_to_dict_with_updated_at(self) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        entity = AdminUserEntity(
            id="ent-3",
            username="dave",
            email="dave@example.com",
            updated_at=now,
        )
        d = self.mapper.map(entity, dict)
        assert d["updated_at"] is not None
        assert "T" in d["updated_at"]  # ISO format
