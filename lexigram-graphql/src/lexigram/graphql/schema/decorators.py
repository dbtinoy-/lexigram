"""GraphQL schema decorators.

This module provides decorator functions for defining GraphQL
resolvers, queries, mutations, and subscriptions using Strawberry.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import functools
from typing import (
    TYPE_CHECKING,
    Any,
    ParamSpec,
    TypeVar,
    cast,
)

import strawberry
from strawberry import Info

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.graphql.core.context import GraphQLContext

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")
R = TypeVar("R")


def query(
    name: str | None = None,
    description: str | None = None,
    deprecation_reason: str | None = None,
    permission_classes: list[Any] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, Any]]:
    """Decorator for marking a method as a GraphQL query.

    This is a wrapper around Strawberry's field decorator with
    additional Lexigram-specific functionality.

    Args:
        name: Optional field name (defaults to function name).
        description: Field description for documentation.
        deprecation_reason: If set, marks the field as deprecated.
        permission_classes: List of permission classes for authorization.

    Returns:
        Decorated function.

    Example:
        ```python
        @strawberry.type
        class Query:
            @query(description="Get user by ID")
            async def user(self, info: Info, id: str) -> User:
                return await get_user(id)
        ```
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Build kwargs for strawberry.field
        field_kwargs: dict[str, Any] = {}

        if name:
            field_kwargs["name"] = name
        if description:
            field_kwargs["description"] = description
        if deprecation_reason:
            field_kwargs["deprecation_reason"] = deprecation_reason
        if permission_classes:
            field_kwargs["permission_classes"] = permission_classes

        # Apply strawberry field decorator
        return cast("Callable[P, T]", strawberry.field(**field_kwargs)(func))

    return decorator


def mutation(
    name: str | None = None,
    description: str | None = None,
    deprecation_reason: str | None = None,
    permission_classes: list[Any] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, Any]]:
    """Decorator for marking a method as a GraphQL mutation.

    This is a wrapper around Strawberry's mutation decorator with
    additional Lexigram-specific functionality.

    Args:
        name: Optional field name (defaults to function name).
        description: Field description for documentation.
        deprecation_reason: If set, marks the field as deprecated.
        permission_classes: List of permission classes for authorization.

    Returns:
        Decorated function.

    Example:
        ```python
        @strawberry.type
        class Mutation:
            @mutation(description="Create a new user")
            async def create_user(
                self, info: Info, input: CreateUserInput
            ) -> User:
                return await create_user(input)
        ```
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Build kwargs for strawberry.mutation
        mutation_kwargs: dict[str, Any] = {}

        if name:
            mutation_kwargs["name"] = name
        if description:
            mutation_kwargs["description"] = description
        if deprecation_reason:
            mutation_kwargs["deprecation_reason"] = deprecation_reason
        if permission_classes:
            mutation_kwargs["permission_classes"] = permission_classes

        # Apply strawberry mutation decorator
        return cast("Callable[P, T]", strawberry.mutation(**mutation_kwargs)(func))

    return decorator


def subscription(
    name: str | None = None,
    description: str | None = None,
    deprecation_reason: str | None = None,
    permission_classes: list[Any] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, Any]]:
    """Decorator for marking a method as a GraphQL subscription.

    This is a wrapper around Strawberry's subscription decorator with
    additional Lexigram-specific functionality.

    Args:
        name: Optional field name (defaults to function name).
        description: Field description for documentation.
        deprecation_reason: If set, marks the field as deprecated.
        permission_classes: List of permission classes for authorization.

    Returns:
        Decorated function.

    Example:
        ```python
        @strawberry.type
        class Subscription:
            @subscription(description="Subscribe to messages")
            async def messages(
                self, info: Info, room_id: str
            ) -> AsyncGenerator[Message, None]:
                async for msg in message_stream(room_id):
                    yield msg
        ```
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Build kwargs for strawberry.subscription
        sub_kwargs: dict[str, Any] = {}

        if name:
            sub_kwargs["name"] = name
        if description:
            sub_kwargs["description"] = description
        if deprecation_reason:
            sub_kwargs["deprecation_reason"] = deprecation_reason
        if permission_classes:
            sub_kwargs["permission_classes"] = permission_classes

        # Apply strawberry subscription decorator
        return cast("Callable[P, T]", strawberry.subscription(**sub_kwargs)(func))

    return decorator


def field(
    name: str | None = None,
    description: str | None = None,
    deprecation_reason: str | None = None,
    default: Any = strawberry.UNSET,
    default_factory: Callable[[], Any] | None = None,
    permission_classes: list[Any] | None = None,
) -> Any:
    """Define a GraphQL field.

    This is a wrapper around Strawberry's field function with
    additional Lexigram-specific functionality.

    Args:
        name: Optional field name.
        description: Field description.
        deprecation_reason: Deprecation reason if deprecated.
        default: Default value.
        default_factory: Factory for default value.
        permission_classes: Permission classes for authorization.

    Returns:
        Strawberry field.

    Example:
        ```python
        @strawberry.type
        class User:
            id: str
            name: str = field(description="User's full name")
            email: str = field(description="User's email address")
        ```
    """
    field_kwargs: dict[str, Any] = {}

    if name:
        field_kwargs["name"] = name
    if description:
        field_kwargs["description"] = description
    if deprecation_reason:
        field_kwargs["deprecation_reason"] = deprecation_reason
    if default is not strawberry.UNSET:
        field_kwargs["default"] = default
    if default_factory:
        field_kwargs["default_factory"] = default_factory
    if permission_classes:
        field_kwargs["permission_classes"] = permission_classes

    return strawberry.field(**field_kwargs)


def resolver(
    name: str | None = None,
    description: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, Any]]:
    """Decorator for field resolvers.

    Use this to define a resolver function that can be used
    as a field resolver in a GraphQL type.

    Args:
        name: Optional resolver name.
        description: ResolverProtocol description.

    Returns:
        Decorated resolver function.

    Example:
        ```python
        @resolver(description="Resolve user's full name")
        async def resolve_full_name(
            root: User, info: Info
        ) -> str:
            return f"{root.first_name} {root.last_name}"

        @strawberry.type
        class User:
            first_name: str
            last_name: str
            full_name: str = strawberry.field(resolver=resolve_full_name)
        ```
    """

    def decorator(func: Callable[P, T]) -> Callable[P, Any]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Support both sync and async resolver functions.
            result = func(*args, **kwargs)
            if isinstance(result, Awaitable):
                return cast("T", await result)
            return result

        # Store metadata (use cast to avoid mypy attribute checks on callables)
        cast("Any", wrapper).__resolver_name__ = name or func.__name__
        cast("Any", wrapper).__resolver_description__ = description

        return wrapper

    return decorator


def get_context(info: Info) -> GraphQLContext:
    """Get the GraphQL context from resolver info.

    Args:
        info: Strawberry resolver info.

    Returns:
        GraphQL context.

    Example:
        ```python
        @strawberry.type
        class Query:
            @strawberry.field
            async def me(self, info: Info) -> User:
                context = get_context(info)
                return context.user
        ```
    """
    return cast("GraphQLContext", info.context)


__all__ = [
    "field",
    "get_context",
    "mutation",
    "query",
    "resolver",
    "subscription",
]
