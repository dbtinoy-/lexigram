"""Integration subpackage — public re-exports."""

from __future__ import annotations

from lexigram.tenancy.integration.cache_decorator import TenantCacheKeyDecorator

__all__ = [
    "TenantCacheKeyDecorator",
]
