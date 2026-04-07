"""Application provider — wires all domain services into the DI container.

:class:`AppProvider` is the *composition root* for the
``lexigram-example-api`` application.  It follows the two-phase pattern:

1. **register** — declare service bindings (no resolution yet).
2. **boot** — resolve dependencies and wire complex object graphs, then
   register controllers so the web layer can resolve them.

This is the *only* place in the application that knows which concrete
implementation is used for each protocol contract.  All other layers depend
on the abstraction (Protocol), never on the concrete type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.core import ProviderPriority
from lexigram.contracts.events.protocols import DomainEventPublisherProtocol
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

from lexigram_example_api.controllers.auth_controller import AuthController
from lexigram_example_api.controllers.todo_controller import TodoController
from lexigram_example_api.repositories.todo_repository import InMemoryTodoRepository
from lexigram_example_api.repositories.user_repository import InMemoryUserRepository
from lexigram_example_api.services.todo_service import TodoService
from lexigram_example_api.services.user_service import UserService

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

    from lexigram_example_api.config import AppConfig

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Minimal in-process event publisher
# ---------------------------------------------------------------------------


class _LoggingEventPublisher:
    """In-process domain event publisher that logs all published events.

    A lightweight stand-in for a real ``EventBusImpl`` that satisfies the
    :class:`~lexigram.contracts.events.protocols.DomainEventPublisherProtocol`.
    Suitable for development, testing, and demos.  Replace with a real
    event bus in production by registering a different binding in
    :class:`AppProvider.register`.
    """

    async def publish(self, event: Any) -> None:
        """Log the published event and return.

        Args:
            event: Any domain event instance.
        """
        event_type = type(event).__name__
        event_id = getattr(event, "event_id", None)
        logger.info(
            "domain_event_published",
            event_type=event_type,
            event_id=str(event_id) if event_id else None,
        )


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class AppProvider(Provider):
    """Composition root for the lexigram-example-api application.

    Registers and wires:
    - In-memory repository implementations for User and Todo.
    - A logging-based domain event publisher.
    - :class:`~lexigram_example_api.services.user_service.UserService`.
    - :class:`~lexigram_example_api.services.todo_service.TodoService`.
    - :class:`~lexigram_example_api.controllers.auth_controller.AuthController`.
    - :class:`~lexigram_example_api.controllers.todo_controller.TodoController`.

    Args:
        config: Application configuration.  When ``None``, defaults are used.
    """

    name = "app"
    priority = ProviderPriority.DOMAIN

    def __init__(self, config: AppConfig | None = None) -> None:
        """Initialise with optional explicit configuration.

        Args:
            config: Application configuration instance.  When ``None``, an
                instance is created from environment variables / defaults.
        """
        super().__init__()
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register singleton bindings during the registration phase.

        Only lightweight, synchronous constructions happen here.
        Async wiring (e.g. resolving already-registered services to build
        controllers) is deferred to :meth:`boot`.

        Args:
            container: The write-only DI registrar.
        """
        from lexigram_example_api.config import AppConfig

        cfg = self._config or AppConfig()

        # Persist config so other providers can resolve it if needed
        container.singleton(AppConfig, cfg)

        # Repositories — bound to their Protocol types for IoC
        user_repo = InMemoryUserRepository()
        todo_repo = InMemoryTodoRepository()
        container.singleton(InMemoryUserRepository, user_repo)
        container.singleton(InMemoryTodoRepository, todo_repo)

        # Event publisher — bound to the protocol contract
        event_publisher = _LoggingEventPublisher()
        container.singleton(DomainEventPublisherProtocol, event_publisher)  # type: ignore[arg-type]

        logger.debug("app_provider_registered")

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Wire the object graph and register controllers.

        Runs *after* all providers have completed registration, so we can
        safely resolve the ``JWTTokenManager`` that was registered by
        :class:`~lexigram.auth.di.bundle_provider.AuthBundleProvider`.

        Args:
            container: The read-only DI resolver (container is now frozen).
        """
        from lexigram.auth.authn.jwt import JWTTokenManager
        from lexigram.auth.authn.security import PasswordHasher

        from lexigram_example_api.config import AppConfig

        cfg = await container.resolve(AppConfig)

        # Resolve auth primitives registered by AuthBundleProvider
        jwt_manager: JWTTokenManager = await container.resolve(JWTTokenManager)
        hasher = PasswordHasher()

        # Repositories
        user_repo = await container.resolve(InMemoryUserRepository)
        todo_repo = await container.resolve(InMemoryTodoRepository)

        # Event publisher
        event_publisher = await container.resolve(DomainEventPublisherProtocol)

        # Services
        user_service = UserService(
            repo=user_repo,
            hasher=hasher,
            jwt_manager=jwt_manager,
            event_publisher=event_publisher,
        )
        todo_service = TodoService(
            repo=todo_repo,
            event_publisher=event_publisher,
        )

        container.singleton(UserService, user_service)
        container.singleton(TodoService, todo_service)

        # Controllers — registered so the web router can resolve them via DI
        auth_controller = AuthController(
            user_service=user_service,
            jwt_manager=jwt_manager,
        )
        todo_controller = TodoController(
            todo_service=todo_service,
            jwt_manager=jwt_manager,
        )

        container.singleton(AuthController, auth_controller)
        container.singleton(TodoController, todo_controller)

        logger.info(
            "app_provider_booted",
            app_name=cfg.app_name,
            debug=cfg.debug,
        )
