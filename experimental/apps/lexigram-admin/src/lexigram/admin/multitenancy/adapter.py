"""Adapters that delegate admin multitenancy to lexigram-tenancy.

When ``lexigram-tenancy`` is installed, ``TenantProviderRegistry`` wraps a
``TenantProviderProtocol`` store and provides the same API as
``TenantRegistry``.  When it is not installed, the original in-memory
``TenantRegistry`` is used as fallback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.multitenancy.models import TenantConfig, TenantNotFoundError
from lexigram.contracts.tenancy.commands import CreateTenantCommand
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.tenancy.protocols import TenantProviderProtocol
    from lexigram.contracts.tenancy.types import TenantInfo

logger = get_logger(__name__)


class TenantProviderRegistry:
    """Adapter that wraps ``TenantProviderProtocol`` as a ``TenantRegistry``-compatible store.

    Methods mirror ``TenantRegistry`` (``add``, ``remove``, ``get``,
    ``get_by_domain``, ``all``, ``exists``).  When a ``provider`` is
    supplied, write operations delegate to the provider and read operations
    fall through to the provider when the local cache misses.
    """

    def __init__(self, provider: TenantProviderProtocol | None = None) -> None:
        self._provider = provider
        self._tenants: dict[str, TenantConfig] = {}
        self._domain_index: dict[str, str] = {}

    async def add(self, config: TenantConfig) -> None:
        """Register a tenant.

        Updates the in-memory cache and, when a provider is available,
        delegates persistence via ``create_tenant``.
        """
        self._tenants[config.tenant_id] = config
        if config.domain:
            self._domain_index[config.domain] = config.tenant_id
        if self._provider is not None:
            cmd = CreateTenantCommand(
                slug=config.tenant_id,
                name=config.name,
                config={"domain": config.domain} if config.domain else {},
                metadata=config.metadata,
            )
            result = await self._provider.create_tenant(cmd)
            if result.is_err():
                logger.warning(
                    "tenant_provider_create_failed",
                    tenant_id=config.tenant_id,
                    error=str(result.unwrap_err()),
                )
        logger.debug("Tenant registered: %s (%s)", config.tenant_id, config.name)

    async def remove(self, tenant_id: str) -> TenantConfig:
        """Remove a tenant from the registry.

        Raises:
            TenantNotFoundError: If the tenant is not registered.
        """
        if tenant_id not in self._tenants:
            raise TenantNotFoundError(tenant_id)
        config = self._tenants.pop(tenant_id)
        self._domain_index.pop(config.domain, None)
        if self._provider is not None:
            result = await self._provider.deactivate_tenant(tenant_id)
            if result.is_err():
                logger.warning(
                    "tenant_provider_deactivate_failed",
                    tenant_id=tenant_id,
                    error=str(result.unwrap_err()),
                )
        return config

    async def get(self, tenant_id: str) -> TenantConfig | None:
        """Return tenant config by ID, or ``None``.

        Falls through to the provider when the local cache misses.
        """
        cached = self._tenants.get(tenant_id)
        if cached is not None:
            return cached
        if self._provider is not None:
            info = await self._provider.get_tenant(tenant_id)
            if info is not None:
                config = _to_tenant_config(info)
                self._tenants[config.tenant_id] = config
                return config
        return None

    async def get_or_raise(self, tenant_id: str) -> TenantConfig:
        """Return tenant config, raising if not found.

        Raises:
            TenantNotFoundError: If the tenant is not registered.
        """
        config = await self.get(tenant_id)
        if config is None:
            raise TenantNotFoundError(tenant_id)
        return config

    def get_by_domain(self, domain: str) -> TenantConfig | None:
        """Return the tenant config for a custom domain, or ``None``.

        Domain lookups are local-cache-only (the protocol does not expose
        domain-based queries).
        """
        tenant_id = self._domain_index.get(domain)
        return self._tenants.get(tenant_id) if tenant_id else None

    async def all(self, *, active_only: bool = False) -> list[TenantConfig]:
        """Return all registered tenants.

        When a provider is available, delegates to the provider for the
        authoritative list; otherwise returns the local cache.
        """
        if self._provider is not None:
            infos = await self._provider.list_tenants(active_only=active_only)
            tenants = [_to_tenant_config(info) for info in infos]
            # Refresh the local cache
            for t in tenants:
                self._tenants[t.tenant_id] = t
                if t.domain:
                    self._domain_index[t.domain] = t.tenant_id
            return tenants
        tenants = list(self._tenants.values())
        if active_only:
            return [t for t in tenants if t.active]
        return tenants

    def exists(self, tenant_id: str) -> bool:
        """Return ``True`` if the tenant is registered.

        Note: checks the local cache only.  The async :meth:`get` should be
        used when provider fallback is needed.
        """
        return tenant_id in self._tenants


def _to_tenant_config(info: TenantInfo) -> TenantConfig:
    """Convert a ``TenantInfo`` protocol type to an internal ``TenantConfig``."""
    return TenantConfig(
        tenant_id=info.tenant_id,
        name=info.name,
        domain=info.config.get("domain", ""),
        active=info.status.value == "active",
        metadata=info.metadata,
    )


async def resolve_tenant_id(
    request: Any,
    *,
    default: str = "",
    header: str = "x-tenant-id",
    cookie: str = "admin_tenant",
    claim: str | None = None,
) -> str:
    """Resolve tenant ID from a request, delegating to ``lexigram-tenancy``
    resolvers when available.

    Resolution order mirrors ``get_tenant_id``:
    1. ``request.state.tenant_id``
    2. ``X-Tenant-Id`` header
    3. Cookie named *cookie*
    4. Subdomain matched against registry
    5. *default*
    """

    # Identity-bound resolution (security): when an authenticated tenant
    # claim exists it wins outright — client-supplied header/cookie values
    # that disagree with it are ignored rather than honored.
    if claim:
        return str(claim)

    # 1. State override
    state_tenant = getattr(getattr(request, "state", None), "tenant_id", None)
    if state_tenant:
        return str(state_tenant)

    # 2. Header
    headers = getattr(request, "headers", {})
    header_val = (
        headers.get(header, "")
        if isinstance(headers, dict)
        else getattr(headers, "get", lambda _k, d="": d)(header, "")
    )
    if header_val:
        return header_val

    # 3. Cookie
    cookies = getattr(request, "cookies", {})
    if isinstance(cookies, dict) and cookie in cookies:
        return cookies[cookie]

    # 4. Subdomain
    url = getattr(request, "url", None)
    if url:
        hostname = getattr(url, "hostname", "") or ""
        parts = hostname.split(".")
        if len(parts) >= 3:
            subdomain = parts[0]
            app_state = getattr(getattr(request, "app", None), "state", None)
            registry: Any = getattr(app_state, "tenant_registry", None)
            if registry and hasattr(registry, "get_by_domain"):
                config = registry.get_by_domain(hostname) or registry.get(subdomain)
                if config:
                    return config.tenant_id

    return default


__all__ = [
    "TenantProviderRegistry",
    "resolve_tenant_id",
]
