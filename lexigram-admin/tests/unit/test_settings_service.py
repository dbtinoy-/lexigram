"""Tests for settings/service.py — SettingsRegistry, SettingDefinition, _cast_value.

Tests data-centric, pure-Python parts of the settings service.
"""

from __future__ import annotations

import pytest

from lexigram.admin.settings.loader import AdminConfigLoader
from lexigram.admin.settings.service import SettingsService
from lexigram.admin.settings.service import SettingsRegistry


class TestSettingsRegistry:
    """Tests for SettingsRegistry class-level registry."""

    def setup_method(self) -> None:
        # Clear registry before each test to avoid cross-test pollution
        SettingsRegistry._definitions.clear()

    def teardown_method(self) -> None:
        SettingsRegistry._definitions.clear()

    def test_get_returns_none_for_unknown_key(self) -> None:
        result = SettingsRegistry.get("nonexistent.key")
        assert result is None

    def test_get_all_empty_initially(self) -> None:
        result = SettingsRegistry.get_all()
        assert result == []

    def test_get_for_scope_empty_initially(self) -> None:
        result = SettingsRegistry.get_for_scope("global")
        assert result == []

    def test_register_and_get(self) -> None:
        from lexigram.admin.settings.service import SettingDefinition

        defn = SettingDefinition.__new__(SettingDefinition)
        defn.key = "site.title"
        defn.scope = ["global"]
        defn.type = "string"
        defn.default = "My Site"
        defn.options = None
        defn.label = "Site Title"
        defn.description = None
        defn.category = "General"
        defn.is_public = True
        defn.validation_rules = None

        SettingsRegistry.register(defn)
        retrieved = SettingsRegistry.get("site.title")
        assert retrieved is defn

    def test_get_all_returns_all_definitions(self) -> None:
        from lexigram.admin.settings.service import SettingDefinition

        def make_defn(key: str, scope: list[str] | None = None) -> SettingDefinition:
            d = SettingDefinition.__new__(SettingDefinition)
            d.key = key
            d.scope = scope or ["global"]
            d.type = "string"
            d.default = None
            d.options = None
            d.label = key
            d.description = None
            d.category = "General"
            d.is_public = False
            d.validation_rules = None
            return d

        d1 = make_defn("key.one", ["global"])
        d2 = make_defn("key.two", ["tenant"])
        SettingsRegistry.register(d1)
        SettingsRegistry.register(d2)

        all_defs = SettingsRegistry.get_all()
        assert len(all_defs) == 2
        keys = {d.key for d in all_defs}
        assert keys == {"key.one", "key.two"}

    def test_get_for_scope_filters_by_scope(self) -> None:
        from lexigram.admin.settings.service import SettingDefinition

        def make_defn(key: str, scope: list[str]) -> SettingDefinition:
            d = SettingDefinition.__new__(SettingDefinition)
            d.key = key
            d.scope = scope
            d.type = "string"
            d.default = None
            d.options = None
            d.label = key
            d.description = None
            d.category = "General"
            d.is_public = False
            d.validation_rules = None
            return d

        d_global = make_defn("global.setting", ["global"])
        d_tenant = make_defn("tenant.setting", ["tenant"])
        d_both = make_defn("both.setting", ["global", "tenant"])

        SettingsRegistry.register(d_global)
        SettingsRegistry.register(d_tenant)
        SettingsRegistry.register(d_both)

        global_defs = SettingsRegistry.get_for_scope("global")
        assert len(global_defs) == 2
        keys = {d.key for d in global_defs}
        assert "global.setting" in keys
        assert "both.setting" in keys
        assert "tenant.setting" not in keys

    def test_overwrite_registration(self) -> None:
        from lexigram.admin.settings.service import SettingDefinition

        d1 = SettingDefinition.__new__(SettingDefinition)
        d1.key = "my.key"
        d1.scope = ["global"]
        d1.type = "string"
        d1.default = "v1"
        d1.options = None
        d1.label = "My Key"
        d1.description = None
        d1.category = "General"
        d1.is_public = False
        d1.validation_rules = None

        d2 = SettingDefinition.__new__(SettingDefinition)
        d2.key = "my.key"
        d2.scope = ["global"]
        d2.type = "int"
        d2.default = 42
        d2.options = None
        d2.label = "My Key v2"
        d2.description = None
        d2.category = "General"
        d2.is_public = False
        d2.validation_rules = None

        SettingsRegistry.register(d1)
        SettingsRegistry.register(d2)

        retrieved = SettingsRegistry.get("my.key")
        assert retrieved is d2


class TestSettingUpdated:
    """Tests for SettingUpdated domain event."""

    def test_fields(self) -> None:
        from lexigram.admin.settings.service import SettingUpdated

        event = SettingUpdated(
            key="site.title",
            value="New Title",
            scope="global",
            scope_id="system",
        )
        assert event.key == "site.title"
        assert event.value == "New Title"
        assert event.scope == "global"
        assert event.scope_id == "system"


class TestRepositoryTypes:
    """Tests for data/adapters/repository/types.py AuditEntry."""

    def test_audit_entry_defaults(self) -> None:
        from lexigram.admin.data.adapters.repository.types import AuditEntry

        entry = AuditEntry(
            action="create",
            entity_type="users",
            entity_id="u1",
        )
        assert entry.action == "create"
        assert entry.entity_type == "users"
        assert entry.entity_id == "u1"
        assert entry.changes is None
        assert entry.user_id is None
        assert entry.timestamp > 0

    def test_audit_entry_with_all_fields(self) -> None:
        from lexigram.admin.data.adapters.repository.types import AuditEntry

        entry = AuditEntry(
            action="update",
            entity_type="posts",
            entity_id="p1",
            changes={"title": "new"},
            user_id="admin",
        )
        assert entry.changes == {"title": "new"}
        assert entry.user_id == "admin"


class _DummyRepo:
    async def find_one(self, **filters):  # noqa: ANN003
        return None

    async def update(self, entity):  # noqa: ANN001
        return entity

    async def create(self, data):  # noqa: ANN001
        return data


class TestAdminEnvConventions:
    def test_loader_parses_double_underscore_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LEX_ADMIN__AUTH__SESSION_LIFETIME", "3600")
        loader = AdminConfigLoader()

        loaded = loader._load_env()

        assert loaded["auth"]["session_lifetime"] == 3600

    def test_service_uses_admin_namespace_for_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        svc = SettingsService(repository=_DummyRepo())

        assert svc._get_from_env("auth.session_lifetime") is None

        monkeypatch.setenv("LEX_ADMIN__AUTH__SESSION_LIFETIME", "3600")

        assert svc._get_from_env("auth.session_lifetime") == "3600"
