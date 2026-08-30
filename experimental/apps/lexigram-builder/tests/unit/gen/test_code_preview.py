"""Tests for the code preview emitter."""

from __future__ import annotations

import pytest

from lexigram_builder.gen.emitters.code_preview import (
    CodePreview,
    PreviewFile,
    emit_code_preview,
)
from lexigram_builder.graph.models import (
    AuthConfig,
    ContractConfig,
    FeatureFlagConfig,
    RateLimitConfig,
    RoleConfig,
)


class TestEmitCodePreview:
    """Tests for emit_code_preview."""

    def test_empty_preview(self) -> None:
        preview = emit_code_preview()
        assert isinstance(preview, CodePreview)
        # Should have at least main.py and di_provider.py
        paths = [f.path for f in preview.files]
        assert "main.py" in paths
        assert "di_provider.py" in paths

    def test_feature_flag_preview(self) -> None:
        preview = emit_code_preview(
            features=(FeatureFlagConfig(name="new_checkout"),)
        )
        paths = [f.path for f in preview.files]
        assert "src/app/features/new_checkout_flag.py" in paths

        flag_file = next(f for f in preview.files if "new_checkout" in f.path)
        assert "NewCheckoutFlag" in flag_file.content
        assert 'key = "new_checkout"' in flag_file.content

    def test_auth_guard_preview(self) -> None:
        preview = emit_code_preview(
            auth_configs=(AuthConfig(name="jwt_auth"),)
        )
        paths = [f.path for f in preview.files]
        assert "src/app/guards/jwt_auth_auth_guard.py" in paths

        guard_file = next(f for f in preview.files if "jwt_auth" in f.path)
        assert "require_auth" in guard_file.content

    def test_role_guard_preview(self) -> None:
        preview = emit_code_preview(
            role_configs=(RoleConfig(name="admin", permissions=("read", "write")),)
        )
        paths = [f.path for f in preview.files]
        assert "src/app/guards/admin_guard.py" in paths

        guard_file = next(f for f in preview.files if "admin_guard" in f.path)
        assert "require_roles" in guard_file.content
        assert '"read"' in guard_file.content
        assert '"write"' in guard_file.content

    def test_rate_limit_preview(self) -> None:
        preview = emit_code_preview(
            rate_limit_configs=(
                RateLimitConfig(
                    name="api_limit",
                    strategy="fixed_window",
                    max_requests=50,
                    window_seconds=30,
                ),
            )
        )
        paths = [f.path for f in preview.files]
        assert "src/app/guards/api_limit_rate_limit.py" in paths

        rl_file = next(f for f in preview.files if "api_limit" in f.path)
        assert "fixed_window" in rl_file.content
        assert "50" in rl_file.content
        assert "30" in rl_file.content

    def test_contract_request_preview(self) -> None:
        preview = emit_code_preview(
            contract_configs=(
                ContractConfig(
                    name="create_order",
                    direction="request",
                    fields="item_id:str, quantity:int",
                ),
            )
        )
        paths = [f.path for f in preview.files]
        assert "src/app/contracts/create_order.py" in paths

        contract_file = next(f for f in preview.files if "create_order" in f.path)
        assert "CreateOrderRequest" in contract_file.content
        assert "item_id" in contract_file.content
        assert "quantity" in contract_file.content

    def test_contract_response_preview(self) -> None:
        preview = emit_code_preview(
            contract_configs=(
                ContractConfig(name="order_view", direction="response", fields="id:int"),
            )
        )
        contract_file = next(f for f in preview.files if "order_view" in f.path)
        assert "OrderViewResponse" in contract_file.content

    def test_contract_both_preview(self) -> None:
        preview = emit_code_preview(
            contract_configs=(
                ContractConfig(name="order_full", direction="both", fields="id:int"),
            )
        )
        contract_file = next(f for f in preview.files if "order_full" in f.path)
        assert "OrderFullRequest" in contract_file.content
        assert "OrderFullResponse" in contract_file.content

    def test_combined_preview(self) -> None:
        preview = emit_code_preview(
            features=(FeatureFlagConfig(name="beta"),),
            auth_configs=(AuthConfig(name="jwt"),),
            role_configs=(RoleConfig(name="admin"),),
            rate_limit_configs=(RateLimitConfig(name="rl"),),
            contract_configs=(ContractConfig(name="order_req", fields="x:int"),),
        )
        paths = [f.path for f in preview.files]
        assert "src/app/features/beta_flag.py" in paths
        assert "src/app/guards/jwt_auth_guard.py" in paths
        assert "src/app/guards/admin_guard.py" in paths
        assert "src/app/guards/rl_rate_limit.py" in paths
        assert "src/app/contracts/order_req.py" in paths
        assert "main.py" in paths

    def test_preview_files_have_language_hint(self) -> None:
        preview = emit_code_preview(
            features=(FeatureFlagConfig(name="test"),)
        )
        for f in preview.files:
            assert f.language == "python"
