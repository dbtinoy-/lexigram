"""Tests for the built-in DeploymentInfoSpec (read-only env-sourced settings)."""

from __future__ import annotations

import pytest

from lexigram.admin.settings.panel.deployment_spec import (
    DeploymentInfoSpec,
    register_spec,
)
from lexigram.admin.settings.panel.registry import ConfigRegistry


class TestDeploymentInfoSpec:
    def test_nodes_are_readonly(self) -> None:
        nodes = DeploymentInfoSpec.get_nodes()
        assert set(nodes) == {"environment", "log_level"}
        assert all(node.readonly for node in nodes.values())

    def test_scope_is_global(self) -> None:
        assert DeploymentInfoSpec.scope == "global"

    def test_store_name_is_env(self) -> None:
        assert DeploymentInfoSpec.store_name == "env"

    @pytest.mark.asyncio
    async def test_values_reflect_env_var_overrides(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADMIN_DEPLOYMENT_ENVIRONMENT", "staging")
        registry = ConfigRegistry()
        register_spec(registry)

        values = await registry.get_values("admin.deployment", store_name="env")
        assert values["environment"] == "staging"

    @pytest.mark.asyncio
    async def test_readonly_save_is_ignored(self) -> None:
        registry = ConfigRegistry()
        register_spec(registry)

        await registry.save_values(
            "admin.deployment", {"environment": "hacked"}, store_name="env"
        )
        values = await registry.get_values("admin.deployment", store_name="env")
        assert values["environment"] != "hacked"