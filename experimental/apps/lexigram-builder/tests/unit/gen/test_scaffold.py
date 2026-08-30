"""Tests for the scaffold emitter."""

from __future__ import annotations

import pytest

from lexigram_builder.gen.emitters.scaffold import (
    ScaffoldResult,
    emit_scaffold_files,
)
from lexigram_builder.graph.models import (
    AuthConfig,
    ContractConfig,
    FeatureFlagConfig,
    RateLimitConfig,
    RoleConfig,
    RouteConfig,
)


class TestEmitScaffoldFiles:
    """Tests for emit_scaffold_files."""

    def test_empty_scaffold(self) -> None:
        result = emit_scaffold_files()
        assert isinstance(result, ScaffoldResult)
        assert "AppModule" in result.main_py
        assert "DI provider" in result.di_provider

    def test_feature_flag_registration(self) -> None:
        result = emit_scaffold_files(
            features=(FeatureFlagConfig(name="new_checkout"),)
        )
        assert "FeatureFlagsModule" in result.main_py
        assert "FeatureFlagsConfig" in result.main_py
        assert "new_checkout" in result.main_py

    def test_multiple_feature_flags(self) -> None:
        result = emit_scaffold_files(
            features=(
                FeatureFlagConfig(name="flag_a"),
                FeatureFlagConfig(name="flag_b"),
            )
        )
        assert "flag_a" in result.main_py
        assert "flag_b" in result.main_py

    def test_auth_guard_imports(self) -> None:
        result = emit_scaffold_files(
            auth_configs=(AuthConfig(name="jwt_auth"),)
        )
        assert "require_auth" in result.main_py

    def test_role_guard_imports(self) -> None:
        result = emit_scaffold_files(
            role_configs=(RoleConfig(name="admin"),)
        )
        assert "require_roles" in result.main_py

    def test_rate_limit_module_emitted(self) -> None:
        result = emit_scaffold_files(
            rate_limit_configs=(
                RateLimitConfig(
                    name="api_limit",
                    strategy="sliding_window",
                    max_requests=100,
                    window_seconds=60,
                ),
            )
        )
        assert len(result.modules) == 1
        module_name, module_content = result.modules[0]
        assert module_name == "api_limit_rate_limit.py"
        assert "sliding_window" in module_content
        assert "100" in module_content

    def test_contract_imports(self) -> None:
        result = emit_scaffold_files(
            contract_configs=(ContractConfig(name="create_order"),)
        )
        assert "create_order" in result.main_py

    def test_combined_scaffold(self) -> None:
        result = emit_scaffold_files(
            features=(FeatureFlagConfig(name="beta"),),
            auth_configs=(AuthConfig(name="jwt"),),
            role_configs=(RoleConfig(name="admin"),),
            rate_limit_configs=(RateLimitConfig(name="rl"),),
            contract_configs=(ContractConfig(name="order_req"),),
        )
        assert "FeatureFlagsModule" in result.main_py
        assert "require_auth" in result.main_py
        assert "require_roles" in result.main_py
        assert len(result.modules) == 1  # rate limit module
