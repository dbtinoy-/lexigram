"""Subdomain-based tenant resolver."""

from __future__ import annotations

from lexigram.contracts.tenancy.types import TenantResolutionContext


class SubdomainTenantResolver:
    """Resolves tenant from the subdomain of the ``Host`` header.

    Given ``base_domain="app.com"`` and a request to ``acme.app.com``,
    returns ``"acme"``.

    Priority 30.

    Attributes:
        name: ``"subdomain"``
        priority: ``30``
    """

    name: str = "subdomain"
    priority: int = 30

    def __init__(self, base_domain: str) -> None:
        """Initialise the resolver.

        Args:
            base_domain: The base domain to strip, e.g. ``"app.com"``.
                The leading dot is added automatically if missing.
        """
        self._base_domain = (
            base_domain if base_domain.startswith(".") else f".{base_domain}"
        )

    async def resolve(self, context: TenantResolutionContext) -> str | None:
        """Extract the subdomain from the ``Host`` header.

        Args:
            context: Immutable request resolution context.

        Returns:
            The subdomain prefix (slug), or ``None`` if the host does not
            match the configured base domain.
        """
        host = context.host
        if not host:
            return None
        # Strip port if present
        host = host.split(":")[0]
        if host.endswith(self._base_domain):
            subdomain = host[: -len(self._base_domain)]
            return subdomain.strip() or None
        return None


__all__ = ["SubdomainTenantResolver"]
