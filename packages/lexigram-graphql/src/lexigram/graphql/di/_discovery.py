"""Backend auto-discovery methods for GraphQLProvider."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, TypeVar, cast

from lexigram.contracts.core import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
    ProviderPriority,
)
from lexigram.contracts.exceptions.container import UnresolvableDependencyError
from lexigram.contracts.web import WebRateLimiterProtocol
from lexigram.di.provider import Provider
from lexigram.graphql import constants as const
from lexigram.graphql.config import GraphQLConfig
from lexigram.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )
    from lexigram.graphql.core.caching import ResponseCache
    from lexigram.graphql.core.context import ContextFactory
    from lexigram.graphql.core.execution import GraphQLExecutorProtocol
    from lexigram.graphql.di.provider import GraphQLProvider
    from lexigram.graphql.monitoring.metrics import MetricsCollectorProtocol

    # Types used only for annotations inside the provider
    from lexigram.graphql.schema.builder import SchemaBuilderProtocol
    from lexigram.graphql.security.rate_limit import UnifiedRateLimiter

_T = TypeVar("_T")

def _require(instance: _T | None, name: str) -> _T:
    """Return *instance* or raise RuntimeError if ``boot()`` has not been called.

    Args:
        instance: The service instance (``None`` until ``boot()`` runs).
        name: Human-readable service class name for the error message.

    Returns:
        The non-None instance.

    Raises:
        RuntimeError: When ``boot()`` has not completed before resolution.
    """
    if instance is None:
        raise RuntimeError(
            f"{name} not initialised. "
            "Ensure GraphQLProvider.boot() has been called before resolving this service.",
        )
    return instance


class _GraphQLDiscoveryMixin:
    """Mixin holding entry-point based backend discovery."""

    if TYPE_CHECKING:
        def __init__(
            self,
            *,
            config: Any = None,
            **kwargs: Any,
        ) -> None: ...
    @classmethod
    def auto_discover(
        cls,
        *packages: str,
        config: GraphQLConfig | None = None,
        **kwargs: Any,
    ) -> GraphQLProvider:
        """Create a ``GraphQLProvider`` by scanning packages for Strawberry types.

        Scans each package recursively for classes decorated with
        ``@strawberry.type`` whose name is ``Query``, ``Mutation``, or
        ``Subscription``.  Use ``@strawberry.type`` plus the naming convention
        or explicitly set ``__graphql_role__ = "query"`` / ``"mutation"`` /
        ``"subscription"`` on the class to override the name-based detection.

        Args:
            *packages: Dotted Python package paths to scan, e.g.
                ``"my_app.graphql"``.
            config: Optional :class:`~lexigram.graphql.config.GraphQLConfig`.
                Falls back to framework defaults when not provided.
            **kwargs: Extra keyword arguments forwarded to
                :class:`GraphQLProvider.__init__`.

        Returns:
            A configured :class:`GraphQLProvider` instance.

        Example::

            app.add_provider(GraphQLProvider.auto_discover("my_app.graphql"))

        In ``my_app/graphql/schema.py``::

            import strawberry

            @strawberry.type
            class Query:
                @strawberry.field
                async def hello(self) -> str:
                    return "world"

            @strawberry.type
            class Mutation:
                @strawberry.mutation
                async def set_name(self, name: str) -> str:
                    return name
        """
        import importlib
        import pkgutil

        query_cls: Any = None
        mutation_cls: Any = None
        subscription_cls: Any = None

        def _is_strawberry_type(obj: Any) -> bool:
            return isinstance(obj, type) and hasattr(obj, "__strawberry_definition__")

        def _scan(pkg_name: str) -> None:
            nonlocal query_cls, mutation_cls, subscription_cls
            try:
                root = importlib.import_module(pkg_name)
            except ImportError:
                logger.debug("graphql.auto_discover.import_failed", package=pkg_name)
                return

            modules_to_scan = [root]
            root_path = getattr(root, "__path__", None)
            if root_path is not None:
                for _finder, modname, _ispkg in pkgutil.walk_packages(
                    root_path,
                    prefix=pkg_name + ".",
                    onerror=lambda n: logger.debug(
                        "graphql.auto_discover.walk_error", module=n
                    ),
                ):
                    try:
                        modules_to_scan.append(importlib.import_module(modname))
                    except Exception:  # noqa: BLE001, S110
                        pass

            for module in modules_to_scan:
                for attr_name in dir(module):
                    try:
                        obj = getattr(module, attr_name)
                    except Exception:  # noqa: BLE001, S112
                        continue
                    if not _is_strawberry_type(obj):
                        continue
                    role: str = (
                        getattr(obj, "__graphql_role__", "").lower()
                        or attr_name.lower()
                    )
                    if role == "query" and query_cls is None:
                        query_cls = obj
                        logger.debug("graphql.auto_discover.query", cls=obj.__name__)
                    elif role == "mutation" and mutation_cls is None:
                        mutation_cls = obj
                        logger.debug("graphql.auto_discover.mutation", cls=obj.__name__)
                    elif role == "subscription" and subscription_cls is None:
                        subscription_cls = obj
                        logger.debug(
                            "graphql.auto_discover.subscription", cls=obj.__name__
                        )

        for pkg in packages:
            _scan(pkg)

        provider = cls(
            config=config,
            query_class=query_cls,
            mutation_class=mutation_cls,
            subscription_class=subscription_cls,
            context_factory_class=kwargs.get("context_factory_class"),
        )
        return cast("GraphQLProvider", provider)
