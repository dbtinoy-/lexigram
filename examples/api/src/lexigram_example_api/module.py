"""Application module — assembles all providers into a single composition root.

:class:`AppModule` is the integration point that wires Lexigram framework
providers with the application-specific :class:`AppProvider`.  Pass the list
returned by :meth:`AppModule.build_providers` to ``Application.add_providers``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.auth import AuthBundleProvider
from lexigram.auth.config import AuthConfig, JWTConfig
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

from lexigram_example_api.controllers.auth_controller import AuthController
from lexigram_example_api.controllers.todo_controller import TodoController
from lexigram_example_api.di.provider import AppProvider

if TYPE_CHECKING:
    from lexigram_example_api.config import AppConfig

logger = get_logger(__name__)


class AppModule:
    """Assembly point for all application providers.

    :class:`AppModule` is a plain class (not a Lexigram ``Provider``) that
    acts as a factory for the ordered provider list consumed by
    :class:`~lexigram.app.base.Application`.  Keeping module assembly here
    avoids scattering provider construction across ``main.py``.

    Example::

        from lexigram import Application
        from lexigram_example_api.module import AppModule
        from lexigram_example_api.config import AppConfig

        cfg = AppConfig()
        app = Application(name=cfg.app_name)
        app.add_providers(AppModule.build_providers(cfg))
    """

    @staticmethod
    def build_providers(config: AppConfig | None = None) -> list[Provider]:
        """Build an ordered list of providers for the application.

        Provider priority values determine boot order:
        - :class:`~lexigram.auth.di.bundle_provider.AuthBundleProvider`
          (``SECURITY = 20``) boots before
        - :class:`AppProvider` (``DOMAIN = 50``) so JWT primitives are
          available when the app provider resolves them in its ``boot`` phase.
        - :class:`~lexigram.web.di.provider.WebProvider` (``PRESENTATION = 80``)
          boots last, after controllers are registered.

        Args:
            config: Application configuration.  When ``None``, defaults are
                loaded from environment variables.

        Returns:
            Ordered list of :class:`~lexigram.di.provider.Provider` instances.
        """
        from lexigram_example_api.config import AppConfig
        from lexigram.web import WebProvider
        from lexigram.web.config import WebConfig, ServerConfig

        cfg = config or AppConfig()

        # Build JWT config from application settings
        jwt_config = JWTConfig(
            secret_key=cfg.jwt_secret,
            algorithm=cfg.jwt_algorithm,
            access_token_expire_minutes=cfg.jwt_expiry_seconds // 60,
        )
        # Both secret_key and token are required fields on AuthConfig
        auth_config = AuthConfig(secret_key=cfg.jwt_secret, token=jwt_config)

        # Web provider — registers controllers for route discovery
        web_config = WebConfig(
            debug=cfg.debug,
            server=ServerConfig(host=cfg.host, port=cfg.port),
        )
        web_provider = WebProvider(
            controllers=[AuthController, TodoController],
            web_config=web_config,
        )

        return [
            AuthBundleProvider(config=auth_config),
            AppProvider(config=cfg),
            web_provider,
        ]
