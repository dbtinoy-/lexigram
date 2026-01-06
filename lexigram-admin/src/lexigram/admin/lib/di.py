"""Dependency Injection utilities for lexigram-admin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol

T = TypeVar("T")


def get_admin_resolver(context: Any | None = None) -> ContainerResolverProtocol:
    """Resolve the current DI resolver for the admin session.

    Prefers the provided context, then falls back to internal contextvars
    if available via contracts.
    """
    from lexigram.di.resolution.context import get_resolver

    # 1. Check provided context
    resolver = get_resolver(context)
    if resolver:
        return resolver

    # 2. Last resort - trigger an error if we can't find anything
    # Ensure the resolver is passed explicitly or available in the request state.
    raise RuntimeError(
        "Could not find a DI resolver in the current admin context. "
        "Ensure the resolver is passed explicitly or available in the request state.",
    )


async def resolve_admin_service(
    service_type: type[T] | str, context: Any | None = None
) -> T:
    """Resolve a service from the admin resolver."""
    resolver = get_admin_resolver(context)
    return await resolver.resolve(service_type)
