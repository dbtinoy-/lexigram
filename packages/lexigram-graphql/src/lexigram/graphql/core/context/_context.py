"""Per-request GraphQL context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Generic, TypeVar
import uuid

from lexigram.contracts.auth import AuthenticatorProtocol
from lexigram.contracts.core import IdGeneratorProtocol
from lexigram.contracts.graphql import (
    GraphQLPrincipal,
    GraphQLPrincipalResolverProtocol,
)
from lexigram.domain import DomainModel
from lexigram.graphql.core.context._models import GraphQLRequest
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.validation import Field

if TYPE_CHECKING:
    from lexigram.graphql.config import GraphQLConfig

logger = get_logger(__name__)


T = TypeVar("T")


@dataclass
class GraphQLContext:
    """GraphQL execution context.

    Provides context for GraphQL operations including
    request information, user data, and configuration.

    Attributes:
        request_id: Unique request identifier.
        user: Current user (if authenticated).
        principal: Resolved principal for identity access across resolvers.
        request: The GraphQL request.
        config: GraphQL configuration.
        started_at: Request start time.
        metadata: Additional context metadata.
        dataloaders: DataLoaderProtocol instances by name.
    """

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user: Any | None = None
    principal: GraphQLPrincipal | None = None
    request: GraphQLRequest | None = None
    config: GraphQLConfig | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)
    dataloaders: dict[str, Any] = field(default_factory=dict)
    raw_request: Any | None = None
    #: Per-request DI scope — dispose via ``await context.dispose_scope()``
    #: after the request completes to release scoped services.
    scope: Any | None = None

    def get_dataloader(self, name: str) -> Any | None:
        """Get a DataLoaderProtocol by name.

        Args:
            name: DataLoaderProtocol name.

        Returns:
            The DataLoaderProtocol instance or None.
        """
        return self.dataloaders.get(name)

    def set_dataloader(self, name: str, loader: Any) -> None:
        """Set a DataLoaderProtocol.

        Args:
            name: DataLoaderProtocol name.
            loader: DataLoaderProtocol instance.
        """
        self.dataloaders[name] = loader

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value.

        Args:
            key: Metadata key.
            default: Default value if not found.

        Returns:
            The metadata value.
        """
        return self.metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value.

        Args:
            key: Metadata key.
            value: Metadata value.
        """
        self.metadata[key] = value

    @property
    def operation_name(self) -> str | None:
        """Get the operation name from request."""
        if self.request:
            return self.request.operation_name
        return None

    @property
    def variables(self) -> dict[str, Any]:
        """Get variables from request."""
        if self.request:
            return self.request.variables
        return {}

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        elapsed = datetime.now(UTC) - self.started_at
        return elapsed.total_seconds() * 1000

    async def dispose_scope(self) -> None:
        """Dispose the per-request DI scope, releasing all scoped services.

        No-op when no scope was created for this context.  The GraphQL
        executor calls this automatically; application code should not
        normally need to call it directly.
        """
        if self.scope is not None and hasattr(self.scope, "dispose"):
            import inspect

            result = self.scope.dispose()
            if inspect.isawaitable(result):
                await result
            self.scope = None
