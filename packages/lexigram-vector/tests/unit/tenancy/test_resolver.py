"""Tests for tenant collection resolvers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pytest


@runtime_checkable
class TenantCollectionResolver(Protocol):
    def resolve(self, logical_name: str, tenant_id: str) -> str: ...


class TestTenantCollectionResolverProtocol:
    """Verify the protocol is structural-typed."""

    def test_is_runtime_checkable(self) -> None:
        from lexigram.contracts.data.vector.tenancy import TenantCollectionResolver
        assert isinstance(TenantCollectionResolver, type)

    def test_resolver_duck_types(self) -> None:
        from lexigram.contracts.data.vector.tenancy import TenantCollectionResolver

        class _Duck:
            def resolve(self, logical_name: str, tenant_id: str) -> str:
                return f"{tenant_id}_{logical_name}"

        assert isinstance(_Duck(), TenantCollectionResolver)


class TestTemplatedTenantCollectionResolver:
    """Tests for the default template-based resolver."""

    def test_default_template(self) -> None:
        from lexigram.vector.tenancy.resolver import (
            TemplatedTenantCollectionResolver,
        )
        resolver = TemplatedTenantCollectionResolver()
        result = resolver.resolve("my_collection", "tenant_abc")
        assert "_t_" in result
        assert "tenant_abc" in result
        assert "my_collection" in result

    def test_default_template_format(self) -> None:
        from lexigram.vector.tenancy.resolver import (
            TemplatedTenantCollectionResolver,
        )
        resolver = TemplatedTenantCollectionResolver()
        result = resolver.resolve("docs", "t1")
        assert result == "docs_t_t1"

    def test_custom_template(self) -> None:
        from lexigram.vector.tenancy.resolver import (
            TemplatedTenantCollectionResolver,
        )
        resolver = TemplatedTenantCollectionResolver(template="{tenant}__{logical}")
        result = resolver.resolve("docs", "t1")
        assert result == "t1__docs"

    def test_implements_protocol(self) -> None:
        from lexigram.contracts.data.vector.tenancy import TenantCollectionResolver
        from lexigram.vector.tenancy.resolver import (
            TemplatedTenantCollectionResolver,
        )
        assert isinstance(TemplatedTenantCollectionResolver(), TenantCollectionResolver)

    def test_different_tenants_different_names(self) -> None:
        from lexigram.vector.tenancy.resolver import (
            TemplatedTenantCollectionResolver,
        )
        resolver = TemplatedTenantCollectionResolver()
        assert resolver.resolve("col", "t1") != resolver.resolve("col", "t2")

    def test_same_tenant_same_name(self) -> None:
        from lexigram.vector.tenancy.resolver import (
            TemplatedTenantCollectionResolver,
        )
        resolver = TemplatedTenantCollectionResolver()
        assert resolver.resolve("col", "t1") == resolver.resolve("col", "t1")


class TestPineconeNamespaceTenantResolver:
    """Tests for the Pinecone namespace-based resolver."""

    def test_returns_logical_name_unchanged(self) -> None:
        from lexigram.vector.tenancy.pinecone_namespace import (
            PineconeNamespaceTenantResolver,
        )
        resolver = PineconeNamespaceTenantResolver()
        result = resolver.resolve("my_index", "tenant_abc")
        assert result == "my_index"

    def test_implements_protocol(self) -> None:
        from lexigram.contracts.data.vector.tenancy import TenantCollectionResolver
        from lexigram.vector.tenancy.pinecone_namespace import (
            PineconeNamespaceTenantResolver,
        )
        assert isinstance(
            PineconeNamespaceTenantResolver(), TenantCollectionResolver
        )

    def test_same_name_for_all_tenants(self) -> None:
        from lexigram.vector.tenancy.pinecone_namespace import (
            PineconeNamespaceTenantResolver,
        )
        resolver = PineconeNamespaceTenantResolver()
        assert resolver.resolve("col", "t1") == resolver.resolve("col", "t2")
