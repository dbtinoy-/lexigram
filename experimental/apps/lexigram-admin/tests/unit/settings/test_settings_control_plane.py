"""Regression coverage for the settings control-plane audit (R57)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from unittest.mock import MagicMock

import pytest

from lexigram.admin.config import AdminConfig
from lexigram.admin.controllers.route_collection import collect_instance_routes
from lexigram.admin.controllers.settings import SettingsController
from lexigram.admin.services.settings_service import AdminSettingsService
from lexigram.admin.settings.application import (
    AdminConfigStore,
    EffectiveApplicationConfigSpec,
    redact_config_value,
)
from lexigram.admin.settings.loader import AdminConfigLoader
from lexigram.admin.settings.panel.nodes import (
    EmailNode,
    JsonNode,
    PydanticConfigSpec,
    StringNode,
    TimezoneNode,
    UrlNode,
)
from lexigram.admin.settings.panel.registry import ConfigRegistry, ReadOnlyStore
from lexigram.admin.settings.store import TenantConfigStore
from lexigram.domain import DomainModel
from lexigram.validation import Field, SecretStr


@dataclass(init=False)
class _TypedModel(DomainModel):
    locale: str = Field(
        default="en",
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$",
    )
    urls: list[str] = Field(default_factory=list)
    email: str = "ops@example.com"
    timezone: str = "UTC"
    url: str = ""
    mode: Literal["safe", "fast"] = "safe"


class _TypedSpec(PydanticConfigSpec):
    namespace = "test.typed"
    model = _TypedModel
    node_overrides = {
        "email": EmailNode,
        "timezone": TimezoneNode,
        "url": UrlNode,
    }


class _Provider:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], Any] = {}

    async def get_config(self, tenant_id: str, key: str) -> Any:
        return self.values.get((tenant_id, key))

    async def get_all_config(self, tenant_id: str) -> dict[str, Any]:
        return {
            key: value
            for (stored_tenant, key), value in self.values.items()
            if stored_tenant == tenant_id
        }

    async def set_config(self, tenant_id: str, key: str, value: Any) -> None:
        self.values[(tenant_id, key)] = value


class TestFalsySettings:
    """Explicit falsy runtime choices survive service round trips."""

    @pytest.mark.asyncio
    async def test_memory_values_do_not_fall_back_by_truthiness(self) -> None:
        service = AdminSettingsService()
        await service.set("tenant-a", "admin.cache.enabled", False)
        await service.set("tenant-a", "admin.cache.default_ttl", 0)
        await service.set("tenant-a", "admin.notifications.email_from", "")

        assert await service.get("tenant-a", "admin.cache.enabled") is False
        assert await service.get("tenant-a", "admin.cache.default_ttl") == 0
        assert await service.get("tenant-a", "admin.notifications.email_from") == ""
        assert await service.contains("tenant-a", "admin.cache.enabled") is True

    @pytest.mark.asyncio
    async def test_database_values_and_presence_are_distinct_from_defaults(
        self,
    ) -> None:
        provider = _Provider()
        service = AdminSettingsService(provider)
        store = TenantConfigStore(service, tenant_id="tenant-a")

        await store.set("admin.cache.enabled", False)
        await store.set("admin.cache.default_ttl", 0)

        assert await store.get("admin.cache.enabled", True) is False
        assert await store.get("admin.cache.default_ttl", 60) == 0
        assert await store.contains("admin.cache.enabled") is True
        assert await store.contains("admin.cache.default_ttl") is True
        assert await store.contains("admin.cache.missing") is False


class TestTypedNodes:
    """Contributor field types retain strict form semantics."""

    def test_common_constraints_are_derived(self) -> None:
        nodes = _TypedSpec.get_nodes()
        assert isinstance(nodes["locale"], StringNode)
        assert nodes["locale"].validation_error("x")
        assert nodes["locale"].validation_error("en_US")
        assert nodes["locale"].validate("en-US") == "en-US"
        assert isinstance(nodes["urls"], JsonNode)
        assert nodes["urls"].validate('["/a", "/b"]') == ["/a", "/b"]
        assert nodes["urls"].validation_error('{"not": "an array"}')
        assert nodes["urls"].validation_error("not-json")
        assert isinstance(nodes["email"], EmailNode)
        assert isinstance(nodes["timezone"], TimezoneNode)
        assert isinstance(nodes["url"], UrlNode)

    def test_email_url_and_timezone_nodes_reject_bad_values(self) -> None:
        assert EmailNode(label="Email").validation_error("not-an-email")
        assert EmailNode(label="Email").validation_error("ops@example.com") is None
        assert UrlNode(label="Logo").validation_error("javascript:alert(1)")
        assert (
            UrlNode(label="Logo").validation_error("https://example.com/logo.svg")
            is None
        )
        assert UrlNode(label="Logo").validation_error("/static/logo.svg") is None
        assert TimezoneNode(label="Timezone").validation_error("Not/AZone")
        assert TimezoneNode(label="Timezone").validation_error("UTC") is None


class TestEffectiveApplicationConfiguration:
    """The application panel is useful, redacted, and write-protected."""

    @pytest.mark.asyncio
    async def test_config_store_redacts_secrets_but_not_duration_fields(self) -> None:
        config = AdminConfig(auth={"session_secret": SecretStr("do-not-render")})
        redacted = redact_config_value(config)
        assert redacted["auth"]["session_secret"] == "[redacted]"
        assert redacted["auth"]["csrf_token_lifetime"] == 3600
        assert redact_config_value(
            {
                "database_url": "postgres://user:password@example/db",
                "logo_url": "/logo.svg",
            }
        ) == {"database_url": "[redacted]", "logo_url": "/logo.svg"}
        assert redact_config_value(
            {
                "apiKey": "do-not-render",
                "token_ttl_hours": 2,
                "session_id": "derived-session-id",
                "password_hash": "derived-password-hash",
            }
        ) == {
            "apiKey": "[redacted]",
            "token_ttl_hours": 2,
            "session_id": "[redacted]",
            "password_hash": "[redacted]",
        }

        store = AdminConfigStore(config)
        rendered = await store.get("admin.application.effective_config")
        assert "do-not-render" not in rendered
        assert "[redacted]" in rendered
        assert await store.contains("admin.application.effective_config") is True
        with pytest.raises(PermissionError):
            await store.set("admin.application.effective_config", "tamper")

    def test_application_spec_contains_only_readonly_nodes(self) -> None:
        assert EffectiveApplicationConfigSpec.store_name == "application"
        assert all(
            node.readonly
            for node in EffectiveApplicationConfigSpec.get_nodes().values()
        )
        registry = ConfigRegistry()
        registry.register_spec(EffectiveApplicationConfigSpec)
        assert registry.get_package_sources() == ["built-in"]

    @pytest.mark.asyncio
    async def test_readonly_store_rejects_batches(self) -> None:
        with pytest.raises(PermissionError):
            await ReadOnlyStore().set_many({"x": 1})


class TestLoaderProvenance:
    """Loader source labels are stable and precedence-aware."""

    @pytest.mark.asyncio
    async def test_yaml_and_environment_provenance(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        path = tmp_path / "application.yaml"
        path.write_text(
            "admin:\n  title: From YAML\n  auth:\n    idle_timeout: 900\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("LEX_ADMIN__TITLE", "From env")
        loader = AdminConfigLoader(yaml_path=path)
        config = await loader.load()

        assert config.title == "From env"
        assert loader.yaml_path == path
        assert loader.get_provenance()["title"] == "environment override"
        assert "YAML" in loader.get_provenance()["auth.idle_timeout"]
        assert loader.get_provenance()["prefix"] == "declared model default"

    @pytest.mark.asyncio
    async def test_loader_defaults_do_not_override_deployment_layers(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        path = tmp_path / "application.yaml"
        path.write_text("admin:\n  title: From YAML\n", encoding="utf-8")
        monkeypatch.setenv("LEX_ADMIN__TITLE", "From env")
        loader = AdminConfigLoader(yaml_path=path, defaults={"title": "Code default"})

        config = await loader.load()

        assert config.title == "From env"
        assert loader.get_provenance()["title"] == "environment override"


def test_history_route_is_materialized_before_namespace_catchall() -> None:
    """The fixed history path must not be swallowed by /{namespace:path}."""
    controller = SettingsController(renderer=MagicMock())
    routes = collect_instance_routes(controller)
    paths = [route.path for route in routes]

    assert paths.index("/settings/history/{namespace:path}") < paths.index(
        "/settings/{namespace:path}"
    )
