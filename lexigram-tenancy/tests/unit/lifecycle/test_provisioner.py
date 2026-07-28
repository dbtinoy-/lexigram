"""Tests for TenantProvisioner."""

from __future__ import annotations

import pytest

from lexigram.contracts.tenancy.errors import TenantError
from lexigram.result import Err, Ok
from lexigram.tenancy.lifecycle.provisioner import TenantProvisioner


class _SuccessStrategy:
    name = "success"

    async def provision_isolation(self, tenant_id: str):
        return Ok(None)

    async def deprovision_isolation(self, tenant_id: str):
        return Ok(None)


class _FailStrategy:
    name = "fail"

    async def provision_isolation(self, tenant_id: str):
        return Err(TenantError("provision failed"))

    async def deprovision_isolation(self, tenant_id: str):
        return Err(TenantError("deprovision failed"))


@pytest.mark.asyncio
async def test_provision_returns_ok_when_strategy_succeeds() -> None:
    """provision() delegates to strategy and returns Ok."""
    provisioner = TenantProvisioner(strategy=_SuccessStrategy(), auto_provision=True)
    result = await provisioner.provision("tenant-abc")
    assert result.is_ok()


@pytest.mark.asyncio
async def test_provision_returns_err_when_strategy_fails() -> None:
    """provision() propagates Err from strategy."""
    provisioner = TenantProvisioner(strategy=_FailStrategy(), auto_provision=True)
    result = await provisioner.provision("tenant-abc")
    assert result.is_err()


@pytest.mark.asyncio
async def test_provision_is_noop_when_auto_provision_false() -> None:
    """When auto_provision=False, provision() returns Ok(None) without calling strategy."""
    provisioner = TenantProvisioner(strategy=_FailStrategy(), auto_provision=False)
    result = await provisioner.provision("tenant-abc")
    assert result.is_ok()


@pytest.mark.asyncio
async def test_deprovision_is_noop_when_auto_provision_false() -> None:
    """When auto_provision=False, deprovision() returns Ok(None)."""
    provisioner = TenantProvisioner(strategy=_FailStrategy(), auto_provision=False)
    result = await provisioner.deprovision("tenant-abc")
    assert result.is_ok()


@pytest.mark.asyncio
async def test_deprovision_returns_ok_when_strategy_succeeds() -> None:
    """deprovision() delegates to strategy and returns Ok."""
    provisioner = TenantProvisioner(strategy=_SuccessStrategy(), auto_provision=True)
    result = await provisioner.deprovision("tenant-abc")
    assert result.is_ok()


@pytest.mark.asyncio
async def test_deprovision_returns_err_when_strategy_fails() -> None:
    """deprovision() propagates Err from strategy."""
    provisioner = TenantProvisioner(strategy=_FailStrategy(), auto_provision=True)
    result = await provisioner.deprovision("tenant-abc")
    assert result.is_err()


@pytest.mark.asyncio
async def test_provision_passes_tenant_id_to_strategy() -> None:
    """provision() passes tenant_id to strategy."""
    captured: list[str] = []

    class _CapturingStrategy:
        name = "capture"

        async def provision_isolation(self, tenant_id: str):
            captured.append(tenant_id)
            return Ok(None)

        async def deprovision_isolation(self, tenant_id: str):
            return Ok(None)

    provisioner = TenantProvisioner(strategy=_CapturingStrategy(), auto_provision=True)
    await provisioner.provision("test-tenant-123")
    assert captured == ["test-tenant-123"]


@pytest.mark.asyncio
async def test_deprovision_passes_tenant_id_to_strategy() -> None:
    """deprovision() passes tenant_id to strategy."""
    captured: list[str] = []

    class _CapturingStrategy:
        name = "capture"

        async def provision_isolation(self, tenant_id: str):
            return Ok(None)

        async def deprovision_isolation(self, tenant_id: str):
            captured.append(tenant_id)
            return Ok(None)

    provisioner = TenantProvisioner(strategy=_CapturingStrategy(), auto_provision=True)
    await provisioner.deprovision("test-tenant-456")
    assert captured == ["test-tenant-456"]


@pytest.mark.asyncio
async def test_provision_returns_none_on_success() -> None:
    """On success, provision() returns None (Ok(None))."""
    provisioner = TenantProvisioner(strategy=_SuccessStrategy(), auto_provision=True)
    result = await provisioner.provision("tenant-xyz")
    assert result.unwrap() is None


@pytest.mark.asyncio
async def test_deprovision_returns_none_on_success() -> None:
    """On success, deprovision() returns None (Ok(None))."""
    provisioner = TenantProvisioner(strategy=_SuccessStrategy(), auto_provision=True)
    result = await provisioner.deprovision("tenant-xyz")
    assert result.unwrap() is None


def test_auto_provision_default_is_true() -> None:
    """Default value for auto_provision is True."""
    provisioner = TenantProvisioner(strategy=_SuccessStrategy())
    assert provisioner._auto_provision is True
