"""Dependency injection container — facade coordinating all DI components."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    Self,
    TypeVar,
    overload,
)

from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.scopes import ServiceScope
from lexigram.contracts.exceptions.provider import ModuleVisibilityError
from lexigram.di.container.registrar import ContainerRegistrarImpl
from lexigram.di.container.resolver import ContainerResolverImpl
from lexigram.di.container.scope import Scope
from lexigram.di.container.validation import ContainerValidator, OrphanedRegistration
from lexigram.di.context import _module_graph, check_visibility, get_current_module
from lexigram.di.extensions.interceptors import InterceptorRegistry
from lexigram.di.extensions.validator import ProtocolValidator
from lexigram.di.module.errors import format_visibility_error
from lexigram.di.resolution.diagnostics import ContainerDiagnostics
from lexigram.di.resolution.injector import DependencyInjector
from lexigram.di.resolution.invoker import FunctionInvoker
from lexigram.di.resolution.registry import ServiceRegistry
from lexigram.di.resolution.resolver import ServiceResolver
from lexigram.di.resolution.type_hints import TypeHintResolverImpl
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable
    import types

    from lexigram.di.extensions.strategies import ResolutionStrategy
    from lexigram.di.resolution.descriptor import ServiceDescriptor
    from lexigram.di.resolution.type_hints import BoundedCache
    from lexigram.di.types import ServiceFactory

T = TypeVar("T")

logger = get_logger(__name__)


class Container(ContainerRegistrarProtocol, ContainerResolverProtocol):
    """Dependency injection container.

    Manages service registration, resolution, and lifecycle.
    Delegates to ContainerRegistrarImpl, ContainerResolverImpl, and ContainerValidator
    for write, read, and validation responsibilities respectively.

    Usage::

        container = Container()
        container.singleton(MyService, MyService())
        container.transient(IRepo, SqlRepo)

        service = await container.resolve(MyService)
    """

    _resolver_obj: ContainerResolverImpl

    def __init__(
        self, parent: Container | None = None, testing_mode: bool = False
    ) -> None:
        self._parent = parent

        # Core resolution infrastructure
        self._type_hint_resolver = TypeHintResolverImpl()
        self._protocol_validator = ProtocolValidator()
        self._registry = ServiceRegistry(
            self._protocol_validator,
            self._type_hint_resolver,
        )
        self._injector = DependencyInjector(self._type_hint_resolver)
        # interceptor support must exist before the resolver is built
        self.interceptor_registry = InterceptorRegistry()
        self.__service_resolver = ServiceResolver(
            self._registry,
            self._injector,
            parent._resolver if parent else None,
            interceptor_registry=self.interceptor_registry,
        )
        # Link injector to resolver for recursive resolution
        self._injector.set_resolver(self.__service_resolver)

        from lexigram.di.resolution.type_hints import BoundedCache

        # Internal cache for type hints and signatures (MAJ-11)
        self._hints_cache: BoundedCache = BoundedCache(maxsize=1024)

        # Diagnostics component
        self._diagnostics = ContainerDiagnostics(
            self._registry, self._type_hint_resolver
        )
        self._invoker = FunctionInvoker(self.__service_resolver, self._hints_cache)  # type: ignore[arg-type]

        # Component facades
        self._registrar = ContainerRegistrarImpl(
            self._registry, testing_mode=testing_mode
        )
        parent_resolver_obj = parent._resolver_obj if parent else None
        self._resolver_obj = ContainerResolverImpl(
            self._registry,
            self.__service_resolver,
            self._invoker,
            self._hints_cache,
            scope_factory=lambda: Scope(self),
            parent_resolver=parent_resolver_obj,
        )
        self._validator = ContainerValidator(self._registry, self._type_hint_resolver)

    # -- Component accessors -----------------------------------------------

    @property
    def registrar(self) -> ContainerRegistrarImpl:
        """Return the write-only registrar component."""
        return self._registrar

    @property
    def resolver(self) -> ContainerResolverImpl:
        """Return the read-only resolver component."""
        return self._resolver_obj

    # -- Internal API for Scope --------------------------------------------

    @property
    def _resolver(self) -> ServiceResolver:
        """Internal: Get the service resolver. For Scope and internal use only."""
        return self.__service_resolver

    def create_invoker(self) -> FunctionInvoker:
        """Create a :class:`~lexigram.di.resolution.invoker.FunctionInvoker` bound to this container.

        Returns a new invoker that shares this container's service resolver and
        type-hint cache, so repeated calls to :meth:`FunctionInvoker.call` benefit
        from the warm cache without exposing the resolver's private attributes.

        Returns:
            A :class:`~lexigram.di.resolution.invoker.FunctionInvoker` configured
            with this container's resolver and hints cache.

        Example::

            invoker = container.create_invoker()
            result = await invoker.call(my_function)
        """
        return FunctionInvoker(self.__service_resolver, self._hints_cache)  # type: ignore[arg-type]

    def _get_descriptor(self, service_type: type) -> ServiceDescriptor | None:
        """Internal: Get descriptor for a service type. For Scope use only."""
        return self._registry.get(service_type)

    async def _create_with_injection(
        self,
        implementation: type,
        service_type: type,
    ) -> Any:
        """Internal: Create instance with DI. For Scope use only."""
        return await self.__service_resolver.create_with_injection(
            implementation, service_type
        )

    # -- Registration ------------------------------------------------------

    def clear(self) -> None:
        """Clear all registered services.

        Raises:
            ContainerError: if the container has been frozen.
        """
        self._registrar.clear()

    def transient(
        self,
        service_type: type[T],
        factory: ServiceFactory[T],
        validate: bool = True,
    ) -> None:
        """Register a transient service (new instance each resolution)."""
        self._registrar.transient(service_type, factory, validate=validate)

    @overload
    def singleton(
        self,
        service_type: type[T],
        instance: T | None = None,
        *,
        name: str | None = None,
        factory: ServiceFactory[T] | None = None,
        validate: bool = True,
    ) -> None: ...

    @overload
    def singleton(
        self,
        service_type: Any,
        instance: Any = None,
        *,
        name: str | None = None,
        factory: Any | None = None,
        validate: bool = True,
    ) -> None: ...

    def singleton(
        self,
        service_type: Any,
        instance: Any = None,
        *,
        name: str | None = None,
        factory: Any | None = None,
        validate: bool = True,
    ) -> None:
        """Register a singleton service (shared instance).

        Pass ``instance`` for a pre-built singleton, or ``factory`` for lazy creation.
        Use ``name`` for named registrations resolvable via ``Annotated[T, Named('...')]]``.
        """
        self._registrar.singleton(
            service_type,
            instance,
            name=name,
            factory=factory,
            validate=validate,
        )

    def scoped(
        self,
        service_type: type[T],
        factory: ServiceFactory[T],
        validate: bool = True,
        *,
        name: str | None = None,
    ) -> None:
        """Register a scoped service (instance per scope)."""
        self._registrar.scoped(service_type, factory, validate=validate, name=name)

    def bind(self, service_type: type[T], instance: T) -> None:
        """Bind a pre-built singleton instance, overwriting any existing binding.

        Unlike ``singleton()``, this works on frozen containers, making it
        suitable for updating singleton instances during the boot phase
        (e.g. wrapping a store with a tenancy decorator).

        The service *must* already be registered as a singleton.

        Args:
            service_type: The registered service type to rebind.
            instance: The replacement singleton instance.
        """
        self._registrar.bind(service_type, instance)

    def override(self, service_type: type[T], instance: T) -> None:
        """Replace a service registration for testing purposes.

        This method is restricted to containers created with ``testing_mode=True``.
        It works even on frozen containers, intended for test scenarios where
        you need to swap a real service with a fake or mock.

        Args:
            service_type: The service type to override.
            instance: The replacement instance.

        Raises:
            ContainerError: If the container is not in testing mode.
            ContainerError: If the service is not registered.
        """
        self._registrar.override(service_type, instance)

    # -- Lifecycle control -------------------------------------------------

    @property
    def is_frozen(self) -> bool:
        """Return ``True`` if this container has been frozen.

        Once frozen, no further service registrations are allowed.
        Use this in tests or startup checks to verify container state.
        """
        return self._registrar.is_frozen

    def freeze(self, validate: bool = True) -> None:
        """Prevent any further service registrations on this container.

        After freezing, calls to ``transient()``, ``singleton()``, ``scoped()``
        or ``clear()`` will raise :class:`~lexigram.exceptions.ContainerError`.
        Freezing is intended to be invoked once the registration phase is complete
        (e.g. after ``ProviderOrchestrator.register_all()``).

        Args:
            validate: When ``True`` (default), runs pre-flight dependency
                validation before freezing. Raises
                :class:`~lexigram.contracts.exceptions.container.ContainerValidationError`
                if any missing dependencies, circular references, or scope
                violations are detected.

        Raises:
            ContainerValidationError: If ``validate=True`` and validation issues
                are found.
        """
        if validate:
            from lexigram.contracts.exceptions.container import ContainerValidationError

            issues = self.validate()
            if issues:
                raise ContainerValidationError(issues)
        self._registrar.freeze()

    # -- Resolution --------------------------------------------------------

    @overload
    async def resolve(
        self, service_type: type[T], *, bypass_visibility: bool = False
    ) -> T: ...

    @overload
    async def resolve(
        self, service_type: Any, *, bypass_visibility: bool = False
    ) -> Any: ...

    async def resolve(
        self, service_type: Any, *, bypass_visibility: bool = False
    ) -> Any:
        """Asynchronously resolve a service by its registered type.

        Args:
            service_type: The service type to resolve.
            bypass_visibility: If True, skip module visibility enforcement.
                Use only in framework-internal resolution paths.

        Returns:
            The resolved service instance.

        Raises:
            ModuleVisibilityError: If the current module context does not
                have visibility over the requested service type.
        """
        if not bypass_visibility:
            if not check_visibility(service_type):
                module = get_current_module()
                consumer_name = module.__name__ if module else "unknown"
                graph = _module_graph.get()

                if (
                    graph is not None
                    and module is not None
                    and hasattr(graph, "find_modules_exporting")
                ):
                    consumer_node = (
                        graph.get_module(module)
                        if hasattr(graph, "get_module")
                        else None
                    )
                    consumer_imports = [
                        imported.__name__
                        for imported in getattr(consumer_node, "imports", [])
                    ]
                    exporting_nodes = graph.find_modules_exporting(service_type)
                    exporting_names = [node.name for node in exporting_nodes]

                    if not exporting_names:
                        return await self.__service_resolver.resolve(service_type)

                    exported_types = sorted(
                        {
                            export.__name__
                            for node in exporting_nodes
                            for export in getattr(node, "exports", [])
                        }
                    )
                    message = format_visibility_error(
                        consumer_module=consumer_name,
                        consumer_provider=consumer_name,
                        provider_module=exporting_names,
                        service_type=service_type.__name__,
                        exported_types=exported_types,
                        consumer_imports=consumer_imports,
                    )
                    hint = (
                        f"Import one of {exporting_names or ['the exporting module']} "
                        f"into {consumer_name}, or make it global."
                    )
                else:
                    message = (
                        f"Module '{consumer_name}' cannot resolve "
                        f"'{service_type.__name__}': not in its exports or global scope"
                    )
                    hint = "Import the module that exports this service, or make it global."

                raise ModuleVisibilityError(
                    message,
                    consumer_module=consumer_name,
                    service_type=service_type.__name__,
                    hint=hint,
                )
        return await self.__service_resolver.resolve(service_type)

    def resolve_sync(self, service_type: type[T]) -> T:
        """Synchronously resolve an already-instantiated singleton.

        This is intended for use in decorators or other synchronous contexts
        where async resolution is not possible. It ONLY works for singletons
        that have already been instantiated (e.g. during boot).

        Args:
            service_type: The service type to resolve.

        Returns:
            The resolved instance.

        Raises:
            UnresolvableDependencyError: If not a singleton or not instantiated.
        """
        descriptor = self._registry.get(service_type)
        if descriptor is not None and descriptor.is_instantiated:
            return descriptor.instance

        if self._parent:
            return self._parent.resolve_sync(service_type)

        from lexigram.contracts.exceptions import UnresolvableDependencyError

        raise UnresolvableDependencyError(
            f"Cannot resolve {service_type} synchronously: "
            "not an instantiated singleton."
        )

    # -- Validation ----------------------------------------------------------

    def validate(self) -> list[str]:
        """Validate the container configuration.

        Checks:
        - All registered services have resolvable dependencies (missing dependencies)
        - No circular dependencies across the entire graph
        - No scope violations (singleton depending on scoped/transient)

        Returns:
            List of validation issues (empty if valid).
        """
        return self._validator.validate()

    def validate_no_orphans(self) -> list[OrphanedRegistration]:
        """Find registrations that no other service depends on.

        This is a development-time validator to identify dead code
        services that are registered but never used.

        Returns:
            List of potentially orphaned registrations.
        """
        return self._validator.validate_no_orphans()

    # -- Query -------------------------------------------------------------

    def has(self, service_type: object) -> bool:
        """Check if a service is explicitly registered."""
        if self._registry.has(service_type):
            return True
        return self._parent.has(service_type) if self._parent else False

    @overload
    async def resolve_optional(self, service_type: type[T]) -> T | None: ...

    @overload
    async def resolve_optional(self, service_type: Any) -> Any | None: ...

    async def resolve_optional(self, service_type: Any) -> Any | None:
        """Resolve a service, returning None if not registered.

        Provides graceful handling for optional dependencies without
        requiring callers to catch exceptions.

        Args:
            service_type: The type to resolve.

        Returns:
            The resolved instance or None if the service is not registered.
        """
        if self.has(service_type):
            return await self.resolve(service_type)
        return None

    @overload
    async def resolve_all(self, service_type: type[T]) -> list[T]: ...

    @overload
    async def resolve_all(self, service_type: Any) -> list[Any]: ...

    async def resolve_all(self, service_type: Any) -> list[Any]:
        """Resolve all registered implementations that are subtypes of a service type.

        Args:
            service_type: The base type whose implementations to resolve.

        Returns:
            A list of resolved instances for matching registrations.
        """
        results: list[Any] = []
        for registered_type in (d.service_type for d in self._registry.all()):
            if isinstance(registered_type, type) and issubclass(
                registered_type,
                service_type,
            ):
                results.append(await self.resolve(registered_type))
        if self._parent:
            results.extend(await self._parent.resolve_all(service_type))
        return results

    def is_singleton(self, service_type: object) -> bool:
        """Check if a service is registered as a singleton."""
        return self._registry.is_singleton(service_type)

    def _registered_services(self) -> list[str]:
        """Get all registered service names."""
        services = {
            getattr(d.service_type, "__name__", str(d.service_type))
            for d in self._registry.all()
        }
        if self._parent:
            services.update(self._parent._registered_services())
        return sorted(services)

    # -- Diagnostics -------------------------------------------------------

    def dump_registrations(self) -> list[dict[str, Any]]:
        """Return a JSON-serialisable snapshot of all container registrations."""
        return self._diagnostics.dump_registrations()

    def dump_dependency_graph(self) -> dict[str, list[str]]:
        """Return an adjacency map of service → direct dependency names."""
        return self._diagnostics.dump_dependency_graph()

    def log_registrations(self) -> None:
        """Log a human-readable table of all container registrations."""
        self._diagnostics.log_registrations()

    # -- Scoping -----------------------------------------------------------

    def create_scope(self) -> Scope:
        """Create a request-scoped resolution context."""
        return Scope(self)

    @asynccontextmanager
    async def scope(self) -> AsyncIterator[Scope]:
        """Async context manager for a request-scoped container.

        Creates a new :class:`~lexigram.di.container.scope.Scope` and
        disposes it automatically when the context exits.

        Usage::

            async with container.scope() as scoped:
                service = await scoped.resolve(UserService)

        Yields:
            A fresh :class:`~lexigram.di.container.scope.Scope` instance.
        """
        s = self.create_scope()
        try:
            yield s
        finally:
            await s.dispose()

    # -- Function calling with DI (Framework internal use only) ------------

    async def _call(
        self,
        func: Callable[..., Awaitable[T] | T],
        *args: Any,
        strategies: list[ResolutionStrategy] | None = None,
        **kwargs: Any,
    ) -> T:
        """Call a function with automatic dependency injection."""
        return await self._invoker.call(
            func,
            *args,
            strategies=strategies,
            **kwargs,
        )

    async def call(
        self,
        func: Callable[..., Awaitable[T] | T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Call a function with dependency injection (Protocol implementation)."""
        return await self._call(func, *args, **kwargs)

    async def dispose(self) -> None:
        """Dispose the container and all internal singletons.

        Iterates through all registered singletons and disposes of those
        that implement AsyncDisposableProtocol or have a close/aclose method.
        """
        logger.debug("container.dispose_started")
        errors: list[Exception] = []

        for descriptor in reversed(list(self._registry.all())):
            if (
                descriptor.scope == ServiceScope.SINGLETON
                and descriptor.instance is not None
            ):
                instance = descriptor.instance
                # The container registers itself as a singleton (ContainerResolverProtocol).
                # Calling dispose() on self would recurse infinitely — skip it.
                if instance is self:
                    continue
                try:
                    if hasattr(instance, "dispose"):
                        result = instance.dispose()
                        if inspect.isawaitable(result):
                            await result
                    elif hasattr(instance, "close"):
                        result = instance.close()
                        if inspect.isawaitable(result):
                            await result
                    elif hasattr(instance, "aclose"):
                        await instance.aclose()
                except asyncio.CancelledError:
                    raise
                except (
                    RuntimeError,
                    OSError,
                    AttributeError,
                    ValueError,
                    TypeError,
                ) as err:
                    logger.warning(
                        "container.dispose_error",
                        type=type(instance).__name__,
                        error=str(err),
                    )
                    errors.append(err)

        self._registry.clear()
        self._hints_cache.clear()

        if errors:
            raise ExceptionGroup("Container dispose errors", errors)

    async def __aenter__(self) -> Self:
        """Enter async context manager - returns self."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit async context manager - disposes the container."""
        await self.dispose()
        logger.debug("container.dispose_completed")


__all__ = ["Container", "OrphanedRegistration", "Scope"]
