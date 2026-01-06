"""GraphQL protocol definitions.

Protocols for GraphQL execution, schema building, data loading,
resolvers, and subscriptions.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    runtime_checkable,
)

# constant used by web layer when registering subscription routes
DEFAULT_SUBSCRIPTIONS_PATH: str = "/graphql/ws"


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lexigram.contracts.core.result import Result
    from lexigram.contracts.exceptions.base import LexigramError
    from lexigram.contracts.graphql.types import GraphQLPrincipal


@runtime_checkable
class GraphQLExecutorProtocol(Protocol):
    """Protocol for GraphQL query execution."""

    async def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        context: Any | None = None,
        operation_name: str | None = None,
    ) -> Result[dict[str, Any], LexigramError]:
        """Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables
            context: Execution context
            operation_name: Operation name for multi-operation queries

        Returns:
            Ok(result_dict) on success; Err(error) on transport-level failure
            (e.g. timeout, schema misconfiguration). GraphQL field-level errors
            are carried inside the Ok value via the ``errors`` key.
        """
        ...


@runtime_checkable
class GraphQLControllerProtocol(Protocol):
    """Marker protocol representing the HTTP controller for GraphQL.

    The web integration only needs to be able to resolve an instance from the
    container; no specific methods are required.
    """


@runtime_checkable
class SchemaBuilderProtocol(Protocol):
    """Protocol for building GraphQL schemas via a fluent interface."""

    def add_type(self, type_class: Any) -> SchemaBuilderProtocol:
        """Add an additional type to the schema.

        Args:
            type_class: The type class to add.

        Returns:
            Self for chaining.
        """
        ...

    def query(self, query_type: Any) -> SchemaBuilderProtocol:
        """Set the root query type.

        Args:
            query_type: The query type class.

        Returns:
            Self for chaining.
        """
        ...

    def mutation(self, mutation_type: Any) -> SchemaBuilderProtocol:
        """Set the root mutation type.

        Args:
            mutation_type: The mutation type class.

        Returns:
            Self for chaining.
        """
        ...

    def subscription(self, subscription_type: Any) -> SchemaBuilderProtocol:
        """Set the root subscription type.

        Args:
            subscription_type: The subscription type class.

        Returns:
            Self for chaining.
        """
        ...

    def add_extension(self, extension: Any) -> SchemaBuilderProtocol:
        """Register a schema extension.

        Args:
            extension: The extension instance (e.g. a Strawberry SchemaExtension).

        Returns:
            Self for chaining.
        """
        ...

    def add_dataloader(
        self,
        name: str,
        factory: Any,
    ) -> SchemaBuilderProtocol:
        """Register a DataLoaderProtocol factory for per-request loader initialisation.

        The factory is called once per request with the current
        :class:`GraphQLContext` as its sole argument and must return a
        DataLoaderProtocol instance.  All registered factories are forwarded to the
        :class:`ContextFactory` so loaders are available at resolve time via
        ``context.get_dataloader(name)``.

        Args:
            name: Unique loader name (used as the key in context).
            factory: Callable ``(context) -> DataLoaderProtocol`` that creates the
                loader for each request.

        Returns:
            Self for chaining.
        """
        ...

    def build(self) -> Any:
        """Build and return the configured GraphQL schema."""
        ...


@runtime_checkable
class DataLoaderProtocol(Protocol):
    """Protocol for GraphQL data loading (N+1 problem solution)."""

    async def load(self, key: Any) -> Any:
        """Load a single item by key."""
        ...

    async def load_many(self, keys: list[Any]) -> list[Any]:
        """Load multiple items by keys."""
        ...

    def prime(self, key: Any, value: Any) -> None:
        """Prime the cache with a key-value pair."""
        ...


@runtime_checkable
class ResolverProtocol(Protocol):
    """Protocol for GraphQL field resolvers."""

    async def resolve(
        self,
        parent: Any,
        args: dict[str, Any],
        context: Any,
        info: Any,
    ) -> Any:
        """Resolve a GraphQL field.

        Args:
            parent: Parent object
            args: Field arguments
            context: Execution context
            info: Field resolution info

        Returns:
            Resolved field value
        """
        ...


@runtime_checkable
class EntityResolverProtocol(Protocol):
    """Protocol for resolving entities in GraphQL federation."""

    async def resolve_reference(
        self,
        reference: dict[str, Any],
        context: Any,
        info: Any,
    ) -> Any | None:
        """Resolve an entity by reference.

        Args:
            reference: Entity reference
            context: Execution context
            info: Resolution info

        Returns:
            Resolved entity or None
        """
        ...


@runtime_checkable
class ValidationRuleProtocol(Protocol):
    """Protocol for GraphQL query validators (depth, complexity, alias, etc.).

    Implementations perform a single focused check on a parsed document
    and raise a :class:`~lexigram.graphql.exceptions.GraphQLError`
    subclass on failure.  A no-op return indicates the document passed.

    All three built-in validators — :class:`DepthLimitValidator`,
    :class:`ComplexityAnalyzer`, and :class:`AliasLimitValidator` —
    satisfy this protocol.
    """

    def validate(self, document: Any) -> None:
        """Validate a GraphQL document; raise on failure.

        Args:
            document: Parsed GraphQL document (a ``graphql-core``
                ``DocumentNode`` in practice, typed as ``Any`` to avoid
                a hard compile-time dependency on ``graphql-core``).

        Raises:
            GraphQLBaseError: If the document violates this rule.
        """
        ...


@runtime_checkable
class SubscriptionHandlerProtocol(Protocol):
    """Protocol for field-level GraphQL subscription resolvers.

    Implementations produce an async iterable of events for a single
    subscription field.  This is the *resolver-level* contract; for the
    WebSocket transport protocol see :class:`WebSocketTransportProtocol`.
    """

    async def subscribe(
        self,
        field_name: str,
        args: dict[str, Any],
        context: Any,
        info: Any,
    ) -> AsyncIterator[Any]:
        """Yield events for the named subscription field.

        Args:
            field_name: Subscription field name
            args: Subscription arguments
            context: Execution context
            info: Field resolution info

        Yields:
            Subscription events
        """
        ...


@runtime_checkable
class SubscriptionAuthHandlerProtocol(Protocol):
    """Protocol for per-subscription authorization checks.

    Invoked during ``_handle_subscribe`` before the subscription is
    established.  Return ``False`` to reject the subscription.

    This is a *per-subscription* check distinct from the connection-level
    authentication performed by ``SubscriptionAuth.authenticate`` during
    ``connection_init``.
    """

    async def authorize(
        self,
        user: Any,
        operation_name: str | None,
        query: str | None,
    ) -> bool:
        """Authorize a subscription request.

        Args:
            user: The authenticated user from the connection context,
                or ``None`` when no authentication handler is configured.
            operation_name: The GraphQL operation name, if provided.
            query: The raw GraphQL query string.

        Returns:
            ``True`` if the subscription is authorized, ``False`` to reject.
        """
        ...


@runtime_checkable
class WebSocketTransportProtocol(Protocol):
    """Protocol for WebSocket-level GraphQL subscription transport.

    Describes the connection-handler contract for classes that manage
    the full lifecycle of a WebSocket subscription session (e.g.
    the ``graphql-transport-ws`` protocol).  It is satisfied structurally
    by :class:`~lexigram.graphql.subscriptions.transport.GraphQLWSTransport`.

    This is deliberately separate from :class:`SubscriptionHandler` which
    operates at the field-resolver level.
    """

    async def handle(self, websocket: Any, app: Any | None = None) -> None:
        """Handle a single WebSocket connection for the entire session.

        Implementations should accept the WebSocket, drive the
        protocol handshake, stream subscription events, and clean up
        on disconnect.

        Args:
            websocket: A ``WebSocketProtocol``-compatible connection
                (typed as ``Any`` to avoid a hard Starlette dependency
                in the contracts layer).
            app: Optional application instance for DI / container
                resolution.
        """
        ...


@runtime_checkable
class MutationHandlerProtocol(Protocol):
    """Protocol for GraphQL mutation handling."""

    async def mutate(
        self,
        field_name: str,
        args: dict[str, Any],
        context: Any,
        info: Any,
    ) -> Any:
        """Handle a GraphQL mutation.

        Args:
            field_name: Mutation field name
            args: Mutation arguments
            context: Execution context
            info: Field info

        Returns:
            Mutation result
        """
        ...


@runtime_checkable
class DirectiveHandlerProtocol(Protocol):
    """Protocol for GraphQL directive handling."""

    def apply_directive(
        self,
        directive_name: str,
        args: dict[str, Any],
        target: Any,
    ) -> Any:
        """Apply a GraphQL directive.

        Args:
            directive_name: Directive name
            args: Directive arguments
            target: Target object to apply directive to

        Returns:
            Modified target object
        """
        ...


@runtime_checkable
class ErrorFormatterProtocol(Protocol):
    """Protocol for formatting GraphQL errors.

    Implementations receive the error only; any request-scoped data
    (e.g. request_id, user) must be accessed via the shared execution context
    rather than as a method parameter.
    """

    def format_error(
        self,
        error: Any,
    ) -> dict[str, Any]:
        """Format a GraphQL error for response.

        Args:
            error: GraphQL error object.

        Returns:
            Formatted error dictionary conforming to the GraphQL error spec.
        """
        ...


@runtime_checkable
class GraphQLRequestProtocol(Protocol):
    """Protocol for HTTP requests processed by the GraphQL controller.

    Decouples ``GraphQLController`` from concrete web-framework types
    (e.g. Starlette ``Request``) so that the graphql package does not
    create a cross-extension import dependency on ``lexigram-web``.

    Any framework request object that exposes these members satisfies
    the protocol at runtime.
    """

    state: Any
    """Mutable per-request state bag (e.g. ``request.state``)."""

    scope: dict[str, Any]
    """ASGI connection scope dictionary."""

    async def json(self) -> Any:
        """Deserialise the request body as JSON.

        Returns:
            Parsed JSON value (typically a ``dict``).
        """
        ...


@runtime_checkable
class IntrospectionHandlerProtocol(Protocol):
    """Protocol for GraphQL introspection.

    Implementations perform full schema introspection and return the
    standard GraphQL introspection result.
    """

    async def introspect(self, context: Any) -> dict[str, Any]:
        """Perform GraphQL introspection.

        Args:
            context: Introspection context

        Returns:
            Introspection result
        """
        ...


@runtime_checkable
class GraphQLPrincipalResolverProtocol(Protocol):
    """Protocol for resolving GraphQL principals from authentication sources.

    Implementations transform raw authentication data (e.g., decoded JWT,
    OAuth2 user object) into a framework-standard :class:`GraphQLPrincipal`
    for use in the GraphQL execution context.

    This decouples the GraphQL layer from authentication implementation
    details and enables consistent principal access across all resolvers.
    """

    async def resolve_principal(
        self,
        user: Any,
        request: Any = None,
    ) -> GraphQLPrincipal:
        """Resolve a GraphQLPrincipal from the authenticated user.

        Args:
            user: Raw authenticated user object from the authentication
                layer (e.g., decoded JWT payload, OAuth2 user dict).
            request: Optional HTTP request object for additional context
                (e.g., extracting headers, client IP).

        Returns:
            A :class:`GraphQLPrincipal` with identity fields populated
            from the authentication source.
        """
        ...


__all__ = [
    "DataLoaderProtocol",
    "DirectiveHandlerProtocol",
    "EntityResolverProtocol",
    "ErrorFormatterProtocol",
    "GraphQLControllerProtocol",
    "GraphQLExecutorProtocol",
    "GraphQLPrincipalResolverProtocol",
    "GraphQLRequestProtocol",
    "IntrospectionHandlerProtocol",
    "MutationHandlerProtocol",
    "ResolverProtocol",
    "SchemaBuilderProtocol",
    "SubscriptionAuthHandlerProtocol",
    "SubscriptionHandlerProtocol",
    "ValidationRuleProtocol",
    "WebSocketTransportProtocol",
]
