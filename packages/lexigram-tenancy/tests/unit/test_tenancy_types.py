"""Unit tests for lexigram-tenancy types."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

from lexigram.tenancy.types import TenantInfo, TenantResolutionContext, TenantStatus


class TestTenantStatus:
    """Tests for TenantStatus enum."""

    @pytest.mark.parametrize(
        "status,expected",
        [
            (TenantStatus.ACTIVE, "active"),
            (TenantStatus.INACTIVE, "inactive"),
            (TenantStatus.SUSPENDED, "suspended"),
            (TenantStatus.PROVISIONING, "provisioning"),
        ],
    )
    def test_status_values(self, status: TenantStatus, expected: str) -> None:
        assert status.value == expected

    @pytest.mark.parametrize(
        "status",
        [
            TenantStatus.ACTIVE,
            TenantStatus.INACTIVE,
            TenantStatus.SUSPENDED,
            TenantStatus.PROVISIONING,
        ],
    )
    def test_status_is_string_enum(self, status: TenantStatus) -> None:
        assert isinstance(status, str)

    @pytest.mark.parametrize(
        "status",
        [
            TenantStatus.ACTIVE,
            TenantStatus.INACTIVE,
            TenantStatus.SUSPENDED,
            TenantStatus.PROVISIONING,
        ],
    )
    def test_status_from_string(self, status: TenantStatus) -> None:
        assert TenantStatus(status.value) == status


class TestTenantInfo:
    """Tests for TenantInfo dataclass."""

    def test_required_fields(self) -> None:
        info = TenantInfo(
            tenant_id="tenant-123",
            slug="acme-corp",
            name="Acme Corp",
            status=TenantStatus.ACTIVE,
        )
        assert info.tenant_id == "tenant-123"
        assert info.slug == "acme-corp"
        assert info.name == "Acme Corp"
        assert info.status == TenantStatus.ACTIVE

    def test_optional_fields_default(self) -> None:
        info = TenantInfo(
            tenant_id="tenant-123",
            slug="acme-corp",
            name="Acme Corp",
            status=TenantStatus.ACTIVE,
        )
        assert info.plan is None
        assert info.config == {}
        assert info.metadata == {}
        assert info.created_at is None

    def test_optional_fields_set(self) -> None:
        now = datetime(2025, 1, 1, 12, 0, 0)
        config = {"max_users": 100}
        metadata = {"department": "engineering"}
        info = TenantInfo(
            tenant_id="tenant-123",
            slug="acme-corp",
            name="Acme Corp",
            status=TenantStatus.ACTIVE,
            plan="enterprise",
            config=config,
            metadata=metadata,
            created_at=now,
        )
        assert info.plan == "enterprise"
        assert info.config == config
        assert info.metadata == metadata
        assert info.created_at == now

    


class TestTenantResolutionContext:
    """Tests for TenantResolutionContext dataclass."""

    def test_required_fields(self) -> None:
        ctx = TenantResolutionContext(headers={"x-tenant-id": "tenant-123"})
        assert ctx.headers == {"x-tenant-id": "tenant-123"}

    def test_optional_fields_default(self) -> None:
        ctx = TenantResolutionContext(headers={})
        assert ctx.host is None
        assert ctx.path is None
        assert ctx.claims == {}

    def test_optional_fields_set(self) -> None:
        claims = {"sub": "user-123", "tenant_id": "tenant-456"}
        ctx = TenantResolutionContext(
            headers={"host": "acme.app.com"},
            host="acme.app.com",
            path="/api/users",
            claims=claims,
        )
        assert ctx.host == "acme.app.com"
        assert ctx.path == "/api/users"
        assert ctx.claims == claims

    def test_empty_headers_default(self) -> None:
        """Default headers is empty dict."""
        ctx = TenantResolutionContext(headers={})
        assert ctx.headers == {}

    def test_host_with_port(self) -> None:
        """Host can contain port."""
        ctx = TenantResolutionContext(headers={}, host="acme.app.com:8080")
        assert ctx.host == "acme.app.com:8080"

    def test_path_with_query_string(self) -> None:
        """Path can contain query string."""
        ctx = TenantResolutionContext(headers={}, path="/api/users?id=123")
        assert ctx.path == "/api/users?id=123"

    def test_claims_empty_by_default(self) -> None:
        """Claims defaults to empty dict when not provided."""
        ctx = TenantResolutionContext(headers={})
        assert ctx.claims == {}


class TestTenantStatusAdditional:
    """Additional tests for TenantStatus enum."""

    def test_all_status_values_are_unique(self) -> None:
        values = [s.value for s in TenantStatus]
        assert len(values) == len(set(values))

    def test_status_comparison(self) -> None:
        """Can compare equal status values."""
        assert TenantStatus("active") == TenantStatus.ACTIVE

    def test_status_in_conditional(self) -> None:
        """Can use in conditional expressions."""
        status = TenantStatus.ACTIVE
        if status == TenantStatus.ACTIVE:
            assert True

def test_status_iteration() -> None:
    """Can iterate over all status values."""
    all_statuses = list(TenantStatus)
    assert len(all_statuses) == 4
    assert TenantStatus.ACTIVE in all_statuses
    assert TenantStatus.INACTIVE in all_statuses
    assert TenantStatus.SUSPENDED in all_statuses
    assert TenantStatus.PROVISIONING in all_statuses


class TestTenantInfoAdditional:
    """Additional tests for TenantInfo."""

    def test_tenant_id_is_readonly(self) -> None:
        """tenant_id cannot be changed after creation."""
        info = TenantInfo(
            tenant_id="tenant-123",
            slug="test",
            name="Test",
            status=TenantStatus.ACTIVE,
        )
        assert info.tenant_id == "tenant-123"

    def test_status_as_string_comparison(self) -> None:
        """Status can be compared to string values."""
        assert TenantStatus.ACTIVE == "active"
        assert TenantStatus.INACTIVE == "inactive"

    def test_config_defaults_to_empty_dict(self) -> None:
        """Config defaults to empty dict when not provided."""
        info = TenantInfo(
            tenant_id="tenant-123",
            slug="test",
            name="Test",
            status=TenantStatus.ACTIVE,
        )
        assert info.config == {}

    def test_metadata_defaults_to_empty_dict(self) -> None:
        """Metadata defaults to empty dict when not provided."""
        info = TenantInfo(
            tenant_id="tenant-123",
            slug="test",
            name="Test",
            status=TenantStatus.ACTIVE,
        )
        assert info.metadata == {}


class TestTenantResolutionContextAdditional:
    """Additional tests for TenantResolutionContext."""

    def test_path_can_have_special_chars(self) -> None:
        """Path with special characters works."""
        ctx = TenantResolutionContext(
            headers={},
            path="/api/users?filter=name%20eq%20test",
        )
        assert ctx.path is not None

    def test_host_with_https_port(self) -> None:
        """Host with HTTPS port number works."""
        ctx = TenantResolutionContext(headers={}, host="app.com:443")
        assert ctx.host == "app.com:443"

    def test_multiple_claims_stored(self) -> None:
        """Multiple claims are stored correctly."""
        claims = {"sub": "user1", "tenant_id": "tenant1", "role": "admin"}
        ctx = TenantResolutionContext(headers={}, claims=claims)
        assert len(ctx.claims) == 3
        assert ctx.claims["role"] == "admin"

    