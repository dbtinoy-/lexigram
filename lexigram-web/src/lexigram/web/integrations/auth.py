"""Authentication integration for WebProvider."""

from __future__ import annotations

import inspect
from typing import Any, cast

from starlette.applications import Starlette

from lexigram.di.container import Container
from lexigram.logging import get_logger

logger = get_logger(__name__)


class AuthIntegration:
    """Handles authentication middleware configuration."""

    @staticmethod
    def _is_invocable_authenticator(candidate: Any) -> bool:
        """Check the candidate can be called as ``authenticate(request)``.

        Args:
            candidate: Resolved service candidate.

        Returns:
            True if the candidate is safe to invoke with a single request argument.
        """
        authenticate = getattr(candidate, "authenticate", None)
        if not callable(authenticate):
            return False
        try:
            signature = inspect.signature(authenticate)
        except (TypeError, ValueError):
            return True
        positional: list[inspect.Parameter] = [
            p
            for p in signature.parameters.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        if positional and positional[0].name in ("self", "cls"):
            positional = positional[1:]
        required = [p for p in positional if p.default is p.empty]
        return len(required) <= 1

    @staticmethod
    async def configure(app: Starlette, container: Container, web_config: Any) -> None:
        """Configure authentication middleware."""
        from lexigram.contracts.auth import IdentityResolverProtocol
        from lexigram.contracts.auth.guard import AuthenticatorProtocol
        from lexigram.contracts.exceptions import ContainerError
        from lexigram.web.middleware.auth import AuthenticationMiddleware

        identity_resolver = None
        try:
            identity_resolver = await container.resolve(
                cast("Any", IdentityResolverProtocol)
            )
        except (LookupError, RuntimeError, ContainerError) as e:
            logger.warning("failed_to_resolve_identity_resolver", error=str(e))

        authenticators = []
        try:
            candidates = await container.resolve_all(
                cast("Any", AuthenticatorProtocol)
            )
            for candidate in candidates:
                if AuthIntegration._is_invocable_authenticator(candidate):
                    authenticators.append(candidate)
                else:
                    logger.warning(
                        "skipped_incompatible_authenticator",
                        service=type(candidate).__name__,
                    )
            logger.info("resolved_authenticators", count=len(authenticators))
        except (LookupError, RuntimeError, ContainerError) as e:
            logger.warning("failed_to_resolve_authenticators", error=str(e))

        app.add_middleware(
            AuthenticationMiddleware,
            authenticators=authenticators,
            exclude_paths=web_config.auth_exclude_paths,
            enable_identity_resolution=web_config.enable_identity_resolution,
            identity_resolver=identity_resolver,
        )
        logger.info("Authentication middleware configured")
