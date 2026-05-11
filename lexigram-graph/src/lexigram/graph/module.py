"""Graph store module for dependency injection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.data.graph.protocols import GraphProtocol, GraphStoreProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.graph.config import GraphConfig


@module()
class GraphModule(Module):
    """Graph storage module — registers GraphStoreProtocol and GraphProtocol.

    Registers :class:`~lexigram.contracts.data.graph.protocols.GraphStoreProtocol`
    and :class:`~lexigram.contracts.data.graph.protocols.GraphProtocol` for
    constructor injection.

    Call :meth:`configure` to configure the graph backend (Neo4j or in-memory),
    or :meth:`stub` for an isolated setup with no external service dependencies.

    Usage::

        from lexigram.graph.config import GraphConfig

        @module(
            imports=[GraphModule.configure(GraphConfig(backend="neo4j"))]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(
        cls,
        config: GraphConfig | dict[str, Any] | None = None,
    ) -> DynamicModule:
        """Create a GraphModule with explicit configuration.

        Args:
            config: :class:`~lexigram.graph.config.GraphConfig`, a plain
                ``dict`` of config values, or ``None`` to use environment
                variable defaults.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.

        Raises:
            TypeError: If *config* is not a ``GraphConfig``, ``dict``, or
                ``None``.

        """
        from lexigram.graph.config import (
            GraphConfig,  # noqa: PLC0415 — circular import avoidance; config depends on constants which imports from here
        )
        from lexigram.graph.di.provider import (
            GraphProvider,  # noqa: PLC0415 — circular import avoidance; provider depends on this module
        )

        if config is not None:
            if isinstance(config, dict):
                provider = GraphProvider(config=GraphConfig(**config))
            else:
                provider = GraphProvider(config=config)
        else:
            provider = GraphProvider()

        return DynamicModule(
            module=cls,
            providers=[provider],
            exports=[GraphStoreProtocol, GraphProtocol],
        )

    @classmethod
    def stub(cls, config: GraphConfig | None = None) -> DynamicModule:
        """Create a GraphModule suitable for unit and integration testing.

        Uses an in-memory backend with no external service dependencies.

        Args:
            config: Optional :class:`~lexigram.graph.config.GraphConfig`
                override.  Uses safe in-memory defaults when ``None``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.

        """
        from lexigram.graph.di.provider import (
            GraphProvider,  # noqa: PLC0415 — circular import avoidance; provider depends on this module
        )

        return DynamicModule(
            module=cls,
            providers=[GraphProvider(config=config)],
            exports=[GraphStoreProtocol, GraphProtocol],
        )


__all__ = ["GraphModule"]
