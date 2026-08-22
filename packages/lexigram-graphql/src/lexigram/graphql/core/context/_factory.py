"""ContextFactory: builds GraphQLContext from ASGI scope."""

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
from lexigram.graphql.core.context._context import GraphQLContext
from lexigram.graphql.core.context._models import GraphQLRequest
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.validation import Field

if TYPE_CHECKING:
    from lexigram.graphql.config import GraphQLConfig

logger = get_logger(__name__)


T = TypeVar("T")


class ContextFactory:
    """Factory for creating GraphQL contexts.

    Provides a standardized way to create execution contexts
    with proper initialization and DataLoaderProtocol setup.
    """

    def __init__(
        self,
        config: GraphQLConfig | None = None,
        dataloader_factories: dict[str, Any] | None = None,
        enable_identity_resolution: bool | None = None,
        resolver: Any | None = None,
        identity: IdGeneratorProtocol | None = None,
    ) -> None:
        """Initialize the context factory.

        Args:
            identity: IdGeneratorProtocol for ID generation.
            config: GraphQL configuration.
            dataloader_factories: Factory functions for DataLoaders.
            enable_identity_resolution: Whether to automatically resolve OAuth IDs to UUIDs.
                If not provided, reads from config if available, otherwise defaults to False (opt-in).
            resolver: Optional DI resolver to use for identity resolution.
        """
        self._config = config
        self._dataloader_factories = dataloader_factories or {}
        self._resolver = resolver
        self._identity = identity

        # Use explicit value, or fall back to config, or default to False
        if enable_identity_resolution is not None:
            self._enable_identity_resolution = enable_identity_resolution
        elif config and hasattr(config, "enable_identity_resolution"):
            self._enable_identity_resolution = config.enable_identity_resolution
        else:
            self._enable_identity_resolution = False

    def _generate_request_id(self) -> str:
        """Generate a request ID."""
        if self._identity is not None:
            return self._identity.generate()
        return str(uuid.uuid4())

    def _get_current_time(self) -> datetime:
        """Get current timestamp."""
        return ambient_clock.now()

    async def create_context(
        self,
        request: GraphQLRequest | None = None,
        user: Any | None = None,
        metadata: dict[str, Any] | None = None,
        raw_request: Any | None = None,
    ) -> GraphQLContext:
        """Create a new GraphQL context.

        This async version properly resolves OAuth external IDs to internal UUIDs
        if the OAuthIdentityStore is available in the container, and optionally
        authenticates and resolves a principal.

        Authentication flow:
        1. If user is provided, use it directly (middleware-authenticated)
        2. If no user but raw_request is available, optionally authenticate
        3. Resolve principal via GraphQLPrincipalResolverProtocol
        4. If no resolver exists but user is present, create fallback principal

        Args:
            request: The GraphQL request.
            user: Current user (from middleware or previous auth).
            metadata: Additional metadata.
            raw_request: The raw HTTP request.

        Returns:
            A new GraphQLContext instance with resolved user ID and principal.
        """
        # Step 1: If no user provided, attempt optional authentication from raw_request
        effective_user = user
        if effective_user is None and raw_request is not None:
            effective_user = await self._optional_authenticate(raw_request)

        # Step 2: Try to resolve OAuth external IDs to internal UUIDs
        resolved_user = await self._resolve_user_identity(effective_user)

        # Step 3: Resolve principal from the user
        principal = await self._resolve_principal(resolved_user, raw_request)

        # Generate request_id and timestamp using injected dependencies
        request_id = self._generate_request_id()
        started_at = self._get_current_time()

        context = GraphQLContext(
            request=request,
            user=resolved_user,
            principal=principal,
            config=self._config,
            metadata=metadata or {},
            raw_request=raw_request,
            request_id=request_id,
            started_at=started_at,
        )

        # Initialize DataLoaders
        for name, factory in self._dataloader_factories.items():
            context.set_dataloader(name, factory(context))

        return context

    def create_context_sync(
        self,
        request: GraphQLRequest | None = None,
        user: Any | None = None,
        metadata: dict[str, Any] | None = None,
        raw_request: Any | None = None,
    ) -> GraphQLContext:
        """Create a GraphQL context synchronously (testing/sync-bridge only).

        .. warning::
            Prefer :meth:`create_context` in production code.  This method
            does **not** perform async identity resolution or principal
            resolution — the ``user`` object is passed through as-is and
            principal is set to None.  Use only in test environments
            or sync integration points that cannot ``await``.

        Args:
            request: The GraphQL request.
            user: Current user (no async identity resolution performed).
            metadata: Additional metadata.
            raw_request: The raw HTTP request.

        Returns:
            A new GraphQLContext instance without async identity or principal resolution.
        """
        scope: Any | None = None
        if self._resolver is not None and hasattr(self._resolver, "create_scope"):
            try:
                scope = self._resolver.create_scope()
            except Exception:  # noqa: BLE001
                scope = None

        # Generate request_id and timestamp using injected dependencies
        request_id = self._generate_request_id()
        started_at = self._get_current_time()

        context = GraphQLContext(
            request=request,
            user=user,
            principal=None,  # No async principal resolution in sync mode
            config=self._config,
            metadata=metadata or {},
            raw_request=raw_request,
            scope=scope,
            request_id=request_id,
            started_at=started_at,
        )

        for name, factory in self._dataloader_factories.items():
            context.set_dataloader(name, factory(context))

        return context

    async def _resolve_user_identity(self, user: Any | None) -> Any | None:
        """Resolve OAuth external IDs to internal UUIDs (async version).

        This method checks if the user object contains an external OAuth ID
        (like Google's sub claim) and resolves it to the internal UUID.

        Args:
            user: The user object from authentication.

        Returns:
            The user object with resolved ID, or original user if resolution fails.
        """
        if user is None:
            return None

        # Check if user has an external ID that needs resolution
        external_id = None
        if isinstance(user, dict):
            external_id = user.get("id") or user.get("user_id") or user.get("sub")
        else:
            external_id = (
                getattr(user, "id", None)
                or getattr(user, "user_id", None)
                or getattr(user, "sub", None)
            )

        if not external_id:
            # No external ID to resolve
            return user

        # Check if it's already a valid UUID (no resolution needed)
        try:
            uuid.UUID(str(external_id))
            return user  # Already a valid UUID
        except (ValueError, TypeError):
            pass  # Not a UUID, need to resolve

        # Resolve via IdentityResolverProtocol (from contracts)
        from lexigram.contracts.auth import IdentityResolverProtocol
        from lexigram.di.resolution.context import get_resolver

        try:
            resolver = get_resolver(self._resolver)
            if resolver:
                # Use the contract from contracts instead of concrete implementation
                identity_resolver = await resolver.resolve_optional(
                    IdentityResolverProtocol
                )
                if identity_resolver:
                    resolved_id = await identity_resolver.resolve_user_id(
                        str(external_id),
                        "google",
                    )

                    if resolved_id:
                        # Create a new user object with resolved ID
                        if isinstance(user, dict):
                            resolved_user = dict(user)
                            resolved_user["id"] = resolved_id
                            resolved_user["_resolved_id"] = resolved_id
                            resolved_user["_original_id"] = external_id
                            return resolved_user
                        # For objects, add resolved attributes
                        resolved_user = user
                        resolved_user._resolved_id = resolved_id
                        return resolved_user
        except (AttributeError, RuntimeError, LookupError) as exc:
            # Resolution failed, return original user.
            logger.debug("user_resolution_failed", error=str(exc))

        return user

    async def _optional_authenticate(self, raw_request: Any) -> Any | None:
        """Optionally authenticate from raw_request when no user is provided.

        This method attempts to resolve an AuthenticatorProtocol from the DI
        container and call authenticate(raw_request) if available.

        Args:
            raw_request: The raw HTTP request object.

        Returns:
            Authenticated user or None if authentication fails or is unavailable.
        """
        if raw_request is None or self._resolver is None:
            return None

        try:
            if not hasattr(self._resolver, "resolve_optional"):
                return None

            authenticator = await self._resolver.resolve_optional(AuthenticatorProtocol)
            if authenticator:
                return await authenticator.authenticate(raw_request)
        except (AttributeError, RuntimeError, LookupError) as exc:
            logger.debug("optional_auth_failed", error=str(exc))

        return None

    async def _resolve_principal(
        self, user: Any | None, raw_request: Any | None
    ) -> GraphQLPrincipal | None:
        """Resolve a GraphQLPrincipal from the authenticated user.

        This method attempts to resolve a GraphQLPrincipalResolverProtocol from
        the DI container and call resolve_principal(user, request) if available.
        Falls back to creating a simple principal with raw_user if no resolver
        is registered but a user exists.

        Args:
            user: The authenticated user object.
            raw_request: The raw HTTP request (for additional context).

        Returns:
            GraphQLPrincipal instance or None if no user exists.
        """
        if user is None:
            return None

        try:
            if self._resolver is not None and hasattr(
                self._resolver, "resolve_optional"
            ):
                principal_resolver: (
                    GraphQLPrincipalResolverProtocol | None
                ) = await self._resolver.resolve_optional(
                    GraphQLPrincipalResolverProtocol
                )
                if principal_resolver:
                    return await principal_resolver.resolve_principal(user, raw_request)
        except (AttributeError, RuntimeError, LookupError) as exc:
            logger.debug("principal_resolution_failed", error=str(exc))

        return GraphQLPrincipal(raw_user=user)

    def register_dataloader(
        self,
        name: str,
        factory: Any,
    ) -> None:
        """Register a DataLoaderProtocol factory.

        Args:
            name: DataLoaderProtocol name.
            factory: Factory function that creates the DataLoaderProtocol.
        """
        self._dataloader_factories[name] = factory

    @staticmethod
    def from_dict(
        data: dict[str, Any],
        request: GraphQLRequest | None = None,
    ) -> GraphQLContext:
        """Create a :class:`GraphQLContext` from a plain dictionary.

        A convenience factory for callers that previously passed ``dict``
        directly to :meth:`GraphQLExecutorProtocol.execute`.  Extracts ``user``,
        ``metadata``, and optionally ``request`` from *data*.

        Args:
            data: Mapping with optional keys ``user``, ``metadata``,
                and ``request``.
            request: Explicit request object; overrides ``data[\"request\"]``
                when provided.

        Returns:
            A fully initialised :class:`GraphQLContext`.

        Example::

            context = ContextFactory.from_dict(
                {\"user\": current_user, \"metadata\": {\"source\": \"api\"}},
            )
            result = await executor.execute(query, context=context)
        """
        resolved_request = request or data.get("request")
        return GraphQLContext(
            request=resolved_request,
            user=data.get("user"),
            principal=None,  # Legacy method doesn't resolve principal
            metadata=data.get("metadata", {}),
        )


