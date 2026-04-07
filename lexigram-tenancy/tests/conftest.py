"""Shared test fixtures for lexigram-tenancy tests."""

from __future__ import annotations

import pytest

from lexigram.contracts.tenancy.commands import CreateTenantCommand
from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus
from lexigram.primitives.context import (
    DEFAULT_KEYS,
    Context,
    ContextVarRegistry,
)
from lexigram.tenancy.stores.memory import InMemoryTenantProvider


def make_context() -> Context:
    """Create a Context with all default keys registered.

    Returns:
        A ready-to-use :class:`~lexigram.primitives.context.Context`.
    """
    registry = ContextVarRegistry()
    for key in DEFAULT_KEYS:
        registry.register_key(key)
    return Context(registry)


@pytest.fixture
def provider() -> InMemoryTenantProvider:
    """Fresh InMemoryTenantProvider per test."""
    return InMemoryTenantProvider()


@pytest.fixture
def active_tenant_info() -> TenantInfo:
    """A pre-built active TenantInfo for use in tests."""
    return TenantInfo(
        tenant_id="tenant-abc",
        slug="acme",
        name="ACME Corp",
        status=TenantStatus.ACTIVE,
    )


@pytest.fixture
def inactive_tenant_info() -> TenantInfo:
    """A pre-built inactive TenantInfo."""
    return TenantInfo(
        tenant_id="tenant-inactive",
        slug="inactive-co",
        name="Inactive Co",
        status=TenantStatus.INACTIVE,
    )


@pytest.fixture
def create_cmd() -> CreateTenantCommand:
    """A default CreateTenantCommand."""
    return CreateTenantCommand(slug="acme", name="ACME Corp")
