"""Application class — the composition root for Lexigram."""

from __future__ import annotations

from contextlib import asynccontextmanager
from enum import StrEnum
import os
from pathlib import Path
import sys
import time
from typing import TYPE_CHECKING, Any, TypeVar

from lexigram.app.exceptions import AppShutdownError
from lexigram.app.invoker import Invoker
from lexigram.app.pipeline import MiddlewarePipeline
from lexigram.config import LexigramConfig
from lexigram.contracts.core import MiddlewarePipelineProtocol, MiddlewareProtocol
from lexigram.contracts.core.config import ConfigProtocol
from lexigram.contracts.core.health import (
    AggregateHealthResult,
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.di.container import Container
from lexigram.di.orchestrator import ProviderOrchestrator
from lexigram.logging import get_logger
from lexigram.logging.configurator import apply_config as _apply_logging_config

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lexigram.di.module.dynamic import DynamicModule
    from lexigram.di.provider import Provider
    from lexigram.logging import LoggerProtocol

T = TypeVar("T")


class AppState(StrEnum):
    """Application lifecycle states."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


class Application:
    """The composition root.

    Usage::

        async with Application.boot(providers=[MyProvider()]) as app:
            # resolve Invoker from the container for entry-point injection
            from lexigram.app.invoker import Invoker
            invoker = await app.container.resolve(Invoker)
            await invoker.invoke(main)

    Or for long-running processes::

        app = Application()
        app.add_provider(MyProvider())
        from lexigram.app import run_application
        await run_application(app)
    """

    def __init__(
        self,
        name: str = "lexigram-app",
        config: LexigramConfig | None = None,
    ) -> None:
        self.name = name
        self._state = AppState.CREATED
        self._container = Container()
        self._container.singleton(type(self), self)
        self._orchestrator = ProviderOrchestrator(self._container)

        self._config = config or LexigramConfig.from_env_profile()
        self._container.singleton(LexigramConfig, self._config)
        self._container.singleton(ConfigProtocol, self._config)

        # Configure logging immediately so all module-level get_logger()
        # calls during subsequent imports use the correct filtering wrapper.
        _apply_logging_config(self._config.logging)
        self._logger: LoggerProtocol = get_logger(name)

        self._middleware: MiddlewarePipeline = MiddlewarePipeline()
        self._container.singleton(MiddlewarePipelineProtocol, self._middleware)

        self._invoker = Invoker(self._container, self._middleware)
        self._container.singleton(Invoker, self._invoker)

        self._modules: list[type | DynamicModule] = []
        self._start_time: float | None = None

        # Secrets registered by the app for boot-time validation.
        # Populated via register_secrets() and register_secrets_from_store();
        # validated in start().
        self._registered_secrets: dict[str, str] = {}
        self._secrets_from_stores: list[
            tuple[Any, list[str]]
        ] = []  # list[tuple[SecretStoreProtocol, list[str]]]
        self._secrets_policy: Any | None = None  # SecretsPolicy | None

    # -- Properties --------------------------------------------------------

    @property
    def state(self) -> AppState:
        """Current application state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if application is running."""
        return self._state == AppState.RUNNING

    @property
    def logger(self) -> LoggerProtocol:
        """Get the application logger."""
        return self._logger

    @property
    def config(self) -> LexigramConfig:
        """Application configuration."""
        return self._config

    @property
    def container(self) -> Container:
        """DI container."""
        return self._container

    @property
    def providers(self) -> list[Provider]:
        """Get all registered providers."""
        return self._orchestrator.providers

    # -- Secrets registration ----------------------------------------------

    def register_secrets(
        self,
        secrets: dict[str, str],
        *,
        policy: Any | None = None,
    ) -> None:
        """Register secrets to be validated before providers boot.

        The framework validates these secrets during :meth:`start`, before any
        provider's ``register()`` is called.  The app declares *what* to
        validate; the framework supplies the logic via
        :class:`~lexigram.config.secrets.SecretsValidator`.

        Args:
            secrets: Mapping of secret name → value.  Names should be
                descriptive (e.g. ``"JWT_SECRET"``), as they appear in
                error messages.
            policy: Optional :class:`~lexigram.config.secrets.SecretsPolicy`
                that controls strictness.  When ``None`` a default policy is
                derived from the active :class:`~lexigram.contracts.core.config.Environment`.

        Example::

            app.register_secrets(
                {
                    "JWT_SECRET": os.environ["JWT_SECRET"],
                    "OAUTH_CLIENT_SECRET": os.environ["OAUTH_CLIENT_SECRET"],
                },
            )
        """
        self._registered_secrets.update(secrets)
        if policy is not None:
            self._secrets_policy = policy

    def register_secrets_from_store(
        self,
        store: Any,
        secret_names: list[str],
        *,
        policy: Any | None = None,
    ) -> None:
        """Register secrets sourced from a SecretStore to be validated before providers boot.

        The framework validates these secrets during :meth:`start`, before any
        provider's ``register()`` is called. Secrets are retrieved from the store
        at validation time and validated using the same
        :class:`~lexigram.config.secrets.SecretsValidator` logic as literal secrets.

        Args:
            store: An implementation of
                :class:`~lexigram.contracts.security.secrets.SecretStoreProtocol`.
            secret_names: List of secret names to retrieve from the store.
                Names should be descriptive (e.g. ``"JWT_SECRET"``), as they
                appear in error messages.
            policy: Optional :class:`~lexigram.config.secrets.SecretsPolicy`
                that controls strictness. When ``None`` a default policy is
                derived from the active :class:`~lexigram.contracts.core.config.Environment`.

        Raises:
            SecretNotFoundError: In strict mode, if any secret is not found in
                the store. In non-strict mode, missing secrets are logged as
                warnings and boot continues.

        Example::

            from lexigram.security.secrets import EnvSecretStore

            app.register_secrets_from_store(
                EnvSecretStore(),
                ["NEXTAUTH_SECRET", "DATABASE_PASSWORD"],
            )
        """
        self._secrets_from_stores.append((store, secret_names))
        if policy is not None:
            self._secrets_policy = policy

    # -- Middleware registration -------------------------------------------

    def add_middleware(self, middleware: MiddlewareProtocol[Any, Any]) -> None:
        """Add a middleware to the application."""
        self._middleware.add(middleware)

    # -- Provider registration ---------------------------------------------

    def add_provider(self, provider: Provider) -> None:
        """Add a provider to be orchestrated.

        Must be called before ``start()``.
        """
        if self._state != AppState.CREATED:
            raise RuntimeError(
                f"Cannot add provider after boot. State: {self._state.value}",
            )
        # Orchestrator will recursively add any sub-providers
        self._orchestrator.add(provider)

    def add_providers(self, providers: list[Provider]) -> None:
        """Add multiple providers. Must be called before ``start()``."""
        for provider in providers:
            self.add_provider(provider)

    def discover_providers(self, *packages: str) -> None:
        """Discover and add Provider subclasses from packages.

        Scans each package recursively for :class:`~lexigram.di.provider.Provider`
        subclasses with a no-argument constructor and registers them.

        Also discovers ``@injectable`` / ``@singleton`` decorated classes and
        schedules them for auto-registration into the container during boot.

        Convention: place providers in ``<module>/provider.py`` or
        ``<module>/providers/`` — any file is scanned.

        Args:
            *packages: Dotted Python package paths to scan, e.g.
                ``"my_platform.modules"``.

        Example::

            app.discover_providers("my_platform.modules", "my_platform.infrastructure")
        """
        from lexigram.app.discovery import discover_injectables, discover_providers

        for provider in discover_providers(list(packages)):
            self.add_provider(provider)

        # Auto-register @injectable / @singleton classes via a thin synthetic provider
        injectables = discover_injectables(list(packages))
        if injectables:
            from lexigram.app._injectable_provider import _InjectableAutoProvider

            self.add_provider(_InjectableAutoProvider(injectables))

    # -- Module registration -----------------------------------------------

    def add_module(self, module: type | Any) -> None:
        """Add a module to the application.

        Modules organize providers and define visibility boundaries.
        Must be called before ``start()``.
        """
        if self._state != AppState.CREATED:
            raise RuntimeError(
                f"Cannot add_module after boot. State: {self._state.value}",
            )
        self._modules.append(module)

    def add_modules(self, modules: list[type | Any]) -> None:
        """Add multiple modules. Must be called before ``start()``."""
        for mod in modules:
            self.add_module(mod)

    def discover_modules(
        self,
        *,
        entry_point_group: str = "lexigram.modules",
        directories: list[str | Path] | None = None,
        enabled: list[str] | None = None,
        disabled: list[str] | None = None,
    ) -> None:
        """Discover Module classes and register them with this application.

        Scans importlib.metadata entry points and optionally filesystem
        directories. Each discovered Module is passed to ``add_module()``,
        ensuring it flows through ``CompiledModuleGraph`` during ``start()``.

        Args:
            entry_point_group: Entry-point group to scan. Default "lexigram.modules".
            directories: Extra filesystem directories to scan.
            enabled: Allowlist of module names (empty = all allowed).
            disabled: Denylist of module names to skip.

        Example::

            app.discover_modules()
            app.discover_modules(directories=["./plugins"], disabled=["dev-only"])
        """
        from lexigram.app.discovery import (
            discover_modules_from_directories,
            discover_modules_from_entry_points,
        )

        discovered = discover_modules_from_entry_points(entry_point_group)

        if directories:
            dir_paths = [Path(d) for d in directories]
            for name, cls in discover_modules_from_directories(dir_paths).items():  # type: ignore[arg-type]
                if name not in discovered:
                    discovered[name] = cls

        disabled_set = set(disabled or [])
        enabled_set = set(enabled or [])

        for name, module_cls in discovered.items():
            if name in disabled_set:
                continue
            if enabled_set and name not in enabled_set:
                continue
            self.add_module(module_cls)

    # -- Lifecycle ---------------------------------------------------------

    async def start(self) -> None:
        """Boot all providers and start the application.

        Phases:
            1. Emit ``ApplicationStarting`` event
            2. Register all providers with the container
            3. Boot all providers (dependency order, parallel where possible)
            4. Resolve ``EventBusProtocol`` from container for lifecycle events
            5. Emit ``ApplicationStarted`` event

        If any phase fails, already-booted providers are shut down
        and the application moves to STOPPED.

        Raises:
            RuntimeError: If application is not in CREATED state.
        """
        if self._state != AppState.CREATED:
            raise RuntimeError(f"Cannot start: state is {self._state.value}")

        self._state = AppState.STARTING
        self._start_time = time.monotonic()
        self._logger.info("application.starting", name=self.name)

        # No longer setting global container as it's an anti-pattern

        try:
            if self._config.discovery.auto_discover:
                cfg = self._config.discovery
                self.discover_modules(
                    entry_point_group=cfg.entry_point_group,
                    directories=cfg.directories or None,  # type: ignore[arg-type]
                    enabled=cfg.enabled_modules or None,
                    disabled=cfg.disabled_modules or None,
                )

            # If modules are registered, use ModuleCompiler to extract and order providers.
            if self._modules:
                from lexigram.di.module.compiler import ModuleCompiler

                compiler = ModuleCompiler()

                # Standalone providers are those added via add_provider()
                standalone = self._orchestrator.providers

                graph = compiler.compile(
                    root_modules=self._modules, standalone_providers=standalone
                )

                # Re-populate orchestrator with ordered providers from the graph.
                # Clear existing to avoid duplication errors during re-registration.
                self._orchestrator.clear_providers()
                self._orchestrator.set_compiled_graph(graph)
                for entry in graph.provider_order:
                    # If it's an instance, add it directly.
                    # If it's a class, DiProvider or CoreModule logic might need to handle it.
                    # For now, we assume the compiler gives us what we need.
                    p = entry.provider if entry.is_instance else entry.provider()
                    self._orchestrator.add(p)  # type: ignore[arg-type]

            # Validate registered secrets BEFORE any provider boots.
            if self._registered_secrets or self._secrets_from_stores:
                self._validate_secrets()

            await self._orchestrator.boot_all(self._container)

            self._state = AppState.RUNNING
            self._logger.info("application.started", name=self.name)
            self._print_banner()
        except BaseException:
            self._logger.exception("application.start_failed", name=self.name)
            import traceback

            sys.stderr.write("\n=== APPLICATION BOOT FAILED ===\n")
            traceback.print_exc()
            sys.stderr.write("================================\n")
            sys.stderr.flush()
            try:
                await self._orchestrator.shutdown()
            except RuntimeError as cleanup_err:
                self._logger.exception(
                    "application.cleanup_failed",
                    error=str(cleanup_err),
                )
            self._state = AppState.STOPPED
            raise

    def _validate_secrets(self) -> None:
        """Run boot-time secrets validation.

        Uses the policy stored on this instance (or derives a default from the
        active environment) to validate all secrets registered via
        :meth:`register_secrets` and :meth:`register_secrets_from_store`.
        """
        from lexigram.config.secrets import SecretsPolicy, SecretsValidator
        from lexigram.contracts.security import SecretNotFoundError

        if self._secrets_policy is not None:
            policy = self._secrets_policy
        else:
            policy = SecretsPolicy.for_environment(self._config.env)

        # Collect all secrets (literals + from stores)
        all_secrets: dict[str, str] = dict(self._registered_secrets)

        # Pull secrets from stores
        for store, secret_names in self._secrets_from_stores:
            for name in secret_names:
                try:
                    value = store.get_secret(name)
                    all_secrets[name] = value
                except SecretNotFoundError:
                    # Treat missing secrets from store like missing literal secrets
                    all_secrets[name] = ""

        validator = SecretsValidator(policy)
        total_count = len(all_secrets)
        self._logger.info(
            "application.secrets_validation",
            name=self.name,
            secret_count=total_count,
            strict=policy.strict,
        )
        validator.validate(all_secrets)

    def _print_banner(self) -> None:
        """Print a diagnostic startup banner when enabled.

        Gated by ``app.show_banner`` config (default: ``True``) and the
        ``LEX_QUIET`` environment variable. Does nothing in non-TTY
        environments (e.g. CI, log aggregators).
        """
        if os.environ.get("LEX_QUIET", "").strip() in ("1", "true", "yes"):
            return
        show = getattr(self._config, "get", lambda _key, default: default)(
            "app.show_banner", True
        )
        if not show:
            return

        try:
            from importlib.metadata import PackageNotFoundError
            from importlib.metadata import version as pkg_version

            lx_version = pkg_version("lexigram")
        except (ImportError, PackageNotFoundError):
            lx_version = "dev"

        py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        provider_count = len(self._orchestrator.providers)
        module_count = len(self._modules)
        width = 60
        sep = "═" * (width - 2)

        lines = [
            f"╔{sep}╗",
            f"║  Lexigram {lx_version:<{width - 14}}║",
            f"║  Python {py_version} {'':>{width - 17}}║",
            "║" + " " * (width - 2) + "║",
            f"║  Providers : {provider_count:<{width - 16}}║",
            f"║  Modules   : {module_count:<{width - 16}}║",
            f"╚{sep}╝",
        ]
        banner_text = "\n".join(lines)
        self._logger.info("application.startup_banner", banner=banner_text)

    async def stop(self) -> None:
        """Shutdown all providers in reverse order.

        Safe to call multiple times. Handles being called from
        STARTING state (failed boot) as well as RUNNING.

        Emits ``ApplicationStopping`` before shutdown and
        ``ApplicationStopped`` after completion.
        """
        if self._state in (AppState.STOPPED, AppState.CREATED):
            return

        if self._state == AppState.STOPPING:
            self._logger.warning("application.already_stopping", name=self.name)
            return

        self._state = AppState.STOPPING
        self._logger.info("application.stopping", name=self.name)

        try:
            await self._orchestrator.shutdown()
            await self._container.dispose()
        except (RuntimeError, ExceptionGroup) as err:
            self._logger.exception(
                "application.shutdown_error",
                error=str(err),
                name=self.name,
            )
            raise AppShutdownError(f"Application shutdown failed: {self.name}") from err
        finally:
            uptime = 0.0
            if self._start_time is not None:
                uptime = time.monotonic() - self._start_time
            self._state = AppState.STOPPED
            self._logger.info(
                "application.stopped",
                name=self.name,
                uptime_seconds=round(uptime, 3),
            )

    async def health_check(self, timeout: float = 5.0) -> AggregateHealthResult:
        """Aggregate health check from all providers.

        Returns an :class:`~lexigram.contracts.core.health.AggregateHealthResult`
        whose ``status`` follows worst-case aggregation across all registered
        provider health checks.
        """
        if self._state != AppState.RUNNING:
            return AggregateHealthResult(
                components=[
                    HealthCheckResult(
                        component=self.name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Application is {self._state.value}",
                    )
                ]
            )

        raw: dict[str, Any] = await self._orchestrator.health_check(timeout)
        return AggregateHealthResult(components=list(raw.values()))

    def _probe_unavailable_result(
        self,
        category: HealthCheckCategory,
    ) -> AggregateHealthResult:
        """Build a probe result when the application is not running."""
        return AggregateHealthResult(
            components=[
                HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Application is {self._state.value}",
                    category=category,
                ),
            ],
        )

    async def liveness(self, timeout: float = 5.0) -> AggregateHealthResult:
        """Run liveness checks for the application."""
        if self._state != AppState.RUNNING:
            return self._probe_unavailable_result(HealthCheckCategory.LIVENESS)
        return await self._orchestrator.run_liveness(timeout)

    async def readiness(self, timeout: float = 5.0) -> AggregateHealthResult:
        """Run readiness checks for the application."""
        if self._state != AppState.RUNNING:
            return self._probe_unavailable_result(HealthCheckCategory.READINESS)
        return await self._orchestrator.run_readiness(timeout)

    async def startup_check(self, timeout: float = 5.0) -> AggregateHealthResult:
        """Run startup checks for the application."""
        if self._state != AppState.RUNNING:
            return self._probe_unavailable_result(HealthCheckCategory.STARTUP)
        return await self._orchestrator.run_startup(timeout)

    # -- Convenience -------------------------------------------------------

    @classmethod
    @asynccontextmanager
    async def boot(
        cls,
        name: str = "lexigram-app",
        providers: list[Provider] | None = None,
        modules: list[Any] | None = None,
        config: LexigramConfig | None = None,
    ) -> AsyncIterator[Application]:
        """Create, start, yield, and guarantee shutdown.

        Usage::

            async with Application.boot(providers=[...]) as app:
                await app.invoke(main)
        """
        app = cls(name=name, config=config)
        if modules:
            app.add_modules(modules)
        if providers:
            app.add_providers(providers)
        await app.start()
        try:
            yield app
        finally:
            await app.stop()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """ASGI entrypoint. Supports both HTTP and lifespan protocols."""
        if scope["type"] == "lifespan":
            await self._handle_lifespan(receive, send)
            return
        handler = getattr(self, "_asgi_handler", None)
        if handler is None and self._state == AppState.CREATED:
            await self.start()
            handler = getattr(self, "_asgi_handler", None)
        if handler is None:
            raise RuntimeError("Application has no ASGI handler registered.")
        await handler(scope, receive, send)

    async def _handle_lifespan(self, receive: Any, send: Any) -> None:
        """Handle ASGI lifespan protocol (startup/shutdown events)."""
        message = await receive()
        if message["type"] == "lifespan.startup":
            try:
                if self._state == AppState.CREATED:
                    await self.start()
                await send({"type": "lifespan.startup.complete"})
            except BaseException:
                await send({"type": "lifespan.startup.failed"})
                raise
        message = await receive()
        if message["type"] == "lifespan.shutdown":
            try:
                await self.stop()
                await send({"type": "lifespan.shutdown.complete"})
            except BaseException:
                await send({"type": "lifespan.shutdown.failed"})
                raise

    def __repr__(self) -> str:
        return f"<Application name={self.name!r} state={self._state.value}>"


__all__ = ["AppState", "Application"]
