"""Authentication and authorization module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.auth import (
    AuthenticatorProtocol,
    AuthorizerProtocol,
    TokenManagerProtocol,
)
from lexigram.contracts.auth.protocols import PasswordHasherProtocol
from lexigram.di.module import DynamicModule, Module, module


@module(is_global=True)
class AuthModule(Module):
    """Full authentication and authorization stack (JWT, OAuth2/OIDC, RBAC, policies).

    Call :meth:`configure` to configure the auth bundle with an
    :class:`~lexigram.auth.config.AuthConfig`.

    Usage::

        from lexigram.auth.config import AuthConfig

        @module(
            imports=[AuthModule.configure(AuthConfig(secret_key="..."))]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(
        cls,
        config: Any | None = None,
        initial_roles: dict[str, Any] | None = None,
        is_global: bool = True,
    ) -> DynamicModule:
        """Create an AuthModule with explicit configuration.

        Args:
            config: :class:`~lexigram.auth.config.AuthConfig` or ``None``
                for framework defaults (development-only ephemeral secrets).
            initial_roles: Optional RBAC role seed forwarded to the
                authorization sub-provider.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.auth.admin.contributor import AuthAdminContributor
        from lexigram.auth.admin.handlers.active_sessions import (
            ActiveSessionsWidgetHandler,
        )
        from lexigram.auth.admin.handlers.failed_logins import FailedLoginsWidgetHandler
        from lexigram.auth.admin.handlers.token_refresh_rate import (
            TokenRefreshRateWidgetHandler,
        )
        from lexigram.auth.di.bundle_provider import AuthBundleProvider

        return DynamicModule(
            module=cls,
            providers=[AuthBundleProvider(config=config, initial_roles=initial_roles)],
            exports=[
                AuthenticatorProtocol,
                AuthorizerProtocol,
                TokenManagerProtocol,
                PasswordHasherProtocol,
                AuthAdminContributor,
                ActiveSessionsWidgetHandler,
                FailedLoginsWidgetHandler,
                TokenRefreshRateWidgetHandler,
            ],
            is_global=is_global,
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return an in-memory AuthModule suitable for unit and integration testing.

        Uses ephemeral in-memory storage with a fixed test secret key.
        No external token services, databases, or OAuth providers are
        configured.

        Args:
            config: Optional test configuration override.

        Returns:
            A DynamicModule backed by in-memory auth storage.
        """
        from lexigram.auth.config import AuthConfig, JWTConfig
        from lexigram.auth.di.bundle_provider import AuthBundleProvider

        return DynamicModule(
            module=cls,
            providers=[
                AuthBundleProvider(
                    config=AuthConfig(
                        secret_key="test-secret-key-for-testing-only",  # noqa: S106  # in-memory test bootstrap
                        token=JWTConfig(
                            secret_key="test-secret-key-for-testing-only",  # noqa: S106  # in-memory test bootstrap
                        ),
                    ),
                    initial_roles=None,
                )
            ],
            exports=[
                AuthenticatorProtocol,
                AuthorizerProtocol,
                TokenManagerProtocol,
                PasswordHasherProtocol,
            ],
        )


__all__ = ["AuthModule"]
