"""Resolution subpackage — public re-exports."""

from __future__ import annotations

from lexigram.tenancy.resolution.chain import CompositeResolver
from lexigram.tenancy.resolution.header import HeaderTenantResolver
from lexigram.tenancy.resolution.jwt_claim import JWTClaimTenantResolver
from lexigram.tenancy.resolution.path import PathTenantResolver
from lexigram.tenancy.resolution.registry import ResolverRegistry
from lexigram.tenancy.resolution.subdomain import SubdomainTenantResolver

__all__ = [
    "CompositeResolver",
    "HeaderTenantResolver",
    "JWTClaimTenantResolver",
    "PathTenantResolver",
    "ResolverRegistry",
    "SubdomainTenantResolver",
]
