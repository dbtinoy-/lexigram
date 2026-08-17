"""Tests for AdminUserEntity — auth/entity.py."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lexigram.admin.auth.entity import AdminUserEntity
from lexigram.admin.auth.user import AdminUserRecord


class TestAdminUserEntity:
    """Tests for AdminUserEntity dataclass."""

    def test_default_id_is_uuid_string(self) -> None:
        entity = AdminUserEntity()
        assert isinstance(entity.id, str)
        assert len(entity.id) == 36  # UUID format

    def test_defaults(self) -> None:
        entity = AdminUserEntity()
        assert entity.username == ""
        assert entity.email == ""
        assert entity.hashed_password == ""
        assert entity.roles == []
        assert entity.permissions == []
        assert entity.is_active is True
        assert entity.is_verified is False
        assert entity.updated_at is None
        assert isinstance(entity.created_at, datetime)

    def test_custom_fields(self) -> None:
        now = datetime.now(UTC)
        entity = AdminUserEntity(
            id="user-123",
            username="alice",
            email="alice@example.com",
            hashed_password="hashed-secret",
            roles=["admin", "editor"],
            permissions=["users.read"],
            is_active=True,
            is_verified=True,
            created_at=now,
            updated_at=now,
        )
        assert entity.id == "user-123"
        assert entity.username == "alice"
        assert entity.email == "alice@example.com"
        assert entity.hashed_password == "hashed-secret"
        assert entity.roles == ["admin", "editor"]
        assert entity.permissions == ["users.read"]
        assert entity.is_active is True
        assert entity.is_verified is True
        assert entity.updated_at == now

    def test_to_user_returns_admin_user_record(self) -> None:
        entity = AdminUserEntity(
            id="user-42",
            username="bob",
            email="bob@example.com",
            hashed_password="pw",
            roles=["viewer"],
            permissions=["posts.read"],
            is_active=True,
            is_verified=True,
        )
        record = entity.to_user()
        assert isinstance(record, AdminUserRecord)
        assert record.user_id == "user-42"
        assert record.name == "bob"
        assert record.email == "bob@example.com"
        assert record.hashed_password == "pw"
        assert record.roles == ["viewer"]
        assert record.permissions == ["posts.read"]
        assert record.is_active is True
        assert record.is_verified is True

    def test_from_user_creates_entity(self) -> None:
        record = AdminUserRecord(
            user_id="user-99",
            name="carol",
            email="carol@example.com",
            hashed_password="hash",
            roles=["superadmin"],
            permissions=["*"],
            is_active=False,
            is_verified=True,
        )
        entity = AdminUserEntity.from_user(record)
        assert entity.id == "user-99"
        assert entity.username == "carol"
        assert entity.email == "carol@example.com"
        assert entity.hashed_password == "hash"
        assert entity.roles == ["superadmin"]
        assert entity.permissions == ["*"]
        assert entity.is_active is False
        assert entity.is_verified is True

    def test_from_user_empty_roles_and_permissions(self) -> None:
        record = AdminUserRecord(
            user_id="user-0",
            email="zero@example.com",
            name="zero",
            roles=[],
            permissions=[],
        )
        entity = AdminUserEntity.from_user(record)
        assert entity.roles == []
        assert entity.permissions == []

    def test_to_user_round_trip(self) -> None:
        original = AdminUserEntity(
            id="round-trip",
            username="roundtrip",
            email="rt@example.com",
            hashed_password="pw123",
            roles=["admin"],
            permissions=["users.list"],
            is_active=True,
            is_verified=True,
        )
        record = original.to_user()
        reconstructed = AdminUserEntity.from_user(record)
        assert reconstructed.id == original.id
        assert reconstructed.username == original.username
        assert reconstructed.email == original.email
        assert reconstructed.roles == original.roles
        assert reconstructed.permissions == original.permissions

    def test_each_entity_gets_unique_id(self) -> None:
        e1 = AdminUserEntity()
        e2 = AdminUserEntity()
        assert e1.id != e2.id
