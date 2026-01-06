"""Header-based tenant resolver."""

from __future__ import annotations

from lexigram.contracts.tenancy.types import TenantResolutionContext


class HeaderTenantResolver:
    """Resolves tenant from an HTTP request header.

    Priority 20 — higher trust than subdomain/path but lower than JWT claim.

    Attributes:
        name: ``"header"``
        priority: ``20``
    """

    name: str = "header"
    priority: int = 20

    def __init__(self, header_name: str = "x-tenant-id") -> None:
        """Initialise the resolver.

        Args:
            header_name: The HTTP header name to read (lowercased).
        """
        self._header_name = header_name.lower()

    async def resolve(self, context: TenantResolutionContext) -> str | None:
        """Return the tenant ID from the configured header.

        Args:
            context: Immutable request resolution context.

        Returns:
            The header value (stripped), or ``None`` if the header is absent
            or empty.
        """
        value = context.headers.get(self._header_name)
        if value:
            return value.strip() or None
        return None


__all__ = ["HeaderTenantResolver"]
