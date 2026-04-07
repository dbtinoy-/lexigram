"""Authentication integration for WebProvider."""

from __future__ import annotations

from typing import Any, cast

from starlette.applications import Starlette

from lexigram.di.container import Container
from lexigram.logging import get_logger

logger = get_logger(__name__)


class AuthIntegration:
    """Handles authentication middleware configuration."""

    @staticmethod
    async def configure(app: Starlette, container: Container, web_config: Any) -> None:
        """Configure authentication middleware."""
        from lexigram.contracts.auth import IdentityResolverProtocol
        from lexigram.contracts.auth.guard import AuthenticatorProtocol
        from lexigram.web.middleware.auth import AuthenticationMiddleware

        identity_resolver = None
        try:
            identity_resolver = await container.resolve(
                cast("Any", IdentityResolverProtocol)
            )
        except (LookupError, RuntimeError) as e:
            logger.warning("failed_to_resolve_identity_resolver", error=str(e))

        authenticators = []
        try:
            authenticators = await container.resolve_all(
                cast("Any", AuthenticatorProtocol)
            )
            logger.info("resolved_authenticators", count=len(authenticators))
        except (LookupError, RuntimeError) as e:
            logger.warning("failed_to_resolve_authenticators", error=str(e))

        app.add_middleware(
            AuthenticationMiddleware,
            authenticators=authenticators,
            exclude_paths=web_config.auth_exclude_paths,
            enable_identity_resolution=web_config.enable_identity_resolution,
            identity_resolver=identity_resolver,
        )
        logger.info("Authentication middleware configured")
