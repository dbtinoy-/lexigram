"""Resolution sub-provider — registers the resolver chain and middleware."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.tenancy.protocols import TenantProviderProtocol
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.tenancy.config import ResolutionConfig
from lexigram.tenancy.enforcement.middleware import TenantContextMiddleware
from lexigram.tenancy.enforcement.validator import TenantValidator
from lexigram.tenancy.resolution.chain import CompositeResolver
from lexigram.tenancy.resolution.registry import ResolverRegistry

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )
    from lexigram.di.resolution.resolver import ServiceResolver

logger = get_logger(__name__)


class TenantResolutionProvider(Provider):
    """Registers the resolver chain, validator, and ASGI middleware.

    Middleware is registered with the web stack only when ``lexigram-web``
    is installed (graceful degradation).
    """

    name = "tenant_resolution"

    def __init__(self, config: ResolutionConfig) -> None:
        """Initialise the provider.

        Args:
            config: Resolution configuration.
        """
        super().__init__()
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register resolver-chain bindings.

        Args:
            container: The DI container registrar.
        """
        registry = ResolverRegistry.from_config(
            resolver_names=self._config.resolvers,
            header_name=self._config.header_name,
            subdomain_pattern=self._config.subdomain_pattern,
            path_pattern=self._config.path_pattern,
            jwt_claim_key=self._config.jwt_claim_key,
        )
        container.singleton(ResolverRegistry, registry)
        container.singleton(CompositeResolver, CompositeResolver(registry))

        cache_ttl = self._config.validator_cache_ttl

        async def _validator_factory(
            resolver: ServiceResolver,
        ) -> TenantValidator:
            provider = await resolver.resolve(TenantProviderProtocol)
            resolve_optional = getattr(resolver, "resolve_optional", None)
            membership = None
            if resolve_optional is not None:
                from lexigram.contracts.tenancy.protocols import (
                    TenantMembershipProtocol,
                )

                try:
                    membership = await resolve_optional(TenantMembershipProtocol)
                except Exception:
                    membership = None  # noqa: BLE001 — optional contract; default-deny applies
            return TenantValidator(
                provider,
                cache_ttl=cache_ttl,
                membership=membership,
                trusted_resolvers=self._config.trusted_resolvers,
                strict_membership=self._config.strict_membership,
            )

        container.singleton(TenantValidator, factory=_validator_factory)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Wire the validator and optionally register middleware.

        Args:
            container: The DI container for boot phase.
        """
        from lexigram.contracts.web.middleware import MiddlewareRegistryProtocol
        from lexigram.primitives.context import Context

        validator = await container.resolve(TenantValidator)

        resolver = await container.resolve(CompositeResolver)

        resolve_optional = getattr(container, "resolve_optional", None)
        if not resolve_optional:
            logger.debug(
                "container_does_not_support_resolve_optional_skipping_middleware"
            )
            return

        try:
            middleware_registry = await resolve_optional(MiddlewareRegistryProtocol)
        except Exception:
            middleware_registry = None

        if middleware_registry is None:
            logger.debug("middleware_registry_not_available_skipping_middleware")
            return

        try:
            ctx = await container.resolve(Context)

            def _middleware_factory(app: object) -> TenantContextMiddleware:
                return TenantContextMiddleware(
                    app=app,  # type: ignore[arg-type]
                    resolver=resolver,
                    validator=validator,
                    ctx=ctx,
                )

            middleware_registry.register_middleware(_middleware_factory)
            logger.debug("tenant_context_middleware_registered")
        except Exception as exc:
            logger.warning("tenant_middleware_registration_failed", error=str(exc))

    async def shutdown(self) -> None:
        """No-op shutdown."""


__all__ = ["TenantResolutionProvider"]
