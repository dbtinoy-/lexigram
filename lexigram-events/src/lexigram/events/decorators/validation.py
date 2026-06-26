"""Validation decorators for CQRS handlers.

This module provides decorators for adding validation to command and query handlers.

Example:
    ```python
    from lexigram.events.decorators import validate, validate_command, idempotent

    @validate
    @command_handler(CreateUserCommand)
    async def handle_create_user(command: CreateUserCommand) -> str:
        # Command is validated before reaching here
        return await user_service.create(command)

    @idempotent(key_func=lambda cmd: cmd.request_id)
    @command_handler(ProcessPaymentCommand)
    async def handle_payment(command: ProcessPaymentCommand) -> str:
        # Idempotent command handling
        return await payment_service.process(command)
    ```
"""

from __future__ import annotations

import functools
from typing import (
    TYPE_CHECKING,
    Any,
    ParamSpec,
    TypeVar,
    cast,
)

from lexigram import hashing  # type: ignore[attr-defined]
from lexigram.contracts.exceptions.domain import ValidationError
from lexigram.events.exceptions import ValidationError as CQRSValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.events.messages import Command

P = ParamSpec("P")
R = TypeVar("R")


# Module-level; modified at runtime by @idempotent wrappers.
# Cleared via clear_idempotency_cache() for test teardown.
_idempotency_cache: dict[str, Any] = {}


def validate(func: Callable[P, Any]) -> Callable[P, Any]:
    """Decorator to validate Pydantic models before handler execution.

    This decorator catches Pydantic ValidationError and converts it
    to a CQRS ValidationError with proper error details.

    Args:
        func: The handler function to wrap.

    Returns:
        Wrapped function with validation.

    Example:
        ```python
        @validate
        @command_handler(CreateUserCommand)
        async def handle_create_user(command: CreateUserCommand) -> str:
            # If command validation fails, CQRSValidationError is raised
            return await user_service.create(command)
        ```
    """

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except ValidationError as e:
            errors: list[str] = []
            errors_list = (
                e.errors()  # type: ignore[operator]
                if callable(getattr(e, "errors", None))
                else getattr(e, "errors", [])
            )
            for error in errors_list:
                if hasattr(error, "get"):  # Pydantic-style dict format
                    loc_val = error.get("loc", [])
                    field = (
                        ".".join(str(loc) for loc in loc_val) if loc_val else "unknown"
                    )
                    msg_val = error.get("msg", "validation error")
                else:  # FieldError object format
                    field = getattr(error, "field", "unknown")
                    msg_val = getattr(error, "message", "validation error")
                errors.append(f"{field}: {msg_val}")
            raise CQRSValidationError(
                f"Validation failed: {'; '.join(errors)}",
                errors=errors_list,
            ) from e

    @functools.wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            errors: list[str] = []
            errors_list = (
                e.errors()  # type: ignore[operator]
                if callable(getattr(e, "errors", None))
                else getattr(e, "errors", [])
            )
            for error in errors_list:
                if hasattr(error, "get"):  # Pydantic-style dict format
                    loc_val = error.get("loc", [])
                    field = (
                        ".".join(str(loc) for loc in loc_val) if loc_val else "unknown"
                    )
                    msg_val = error.get("msg", "validation error")
                else:  # FieldError object format
                    field = getattr(error, "field", "unknown")
                    msg_val = getattr(error, "message", "validation error")
                errors.append(f"{field}: {msg_val}")
            raise CQRSValidationError(
                f"Validation failed: {'; '.join(errors)}",
                errors=errors_list,
            ) from e

    import asyncio

    if asyncio.iscoroutinefunction(func):
        return cast("Callable[P, Any]", async_wrapper)
    return cast("Callable[P, Any]", sync_wrapper)


def validate_command(
    *,
    max_length: dict[str, int] | None = None,
    required_fields: list[str] | None = None,
    custom_validators: list[Callable[[Command], None]] | None = None,
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """Decorator to add custom validation rules to command handlers.

    Args:
        max_length: Dict mapping field names to maximum lengths.
        required_fields: List of fields that must not be None or empty.
        custom_validators: List of custom validation functions.

    Returns:
        Decorator function.

    Example:
        ```python
        @validate_command(
            max_length={"username": 50, "email": 100},
            required_fields=["username", "email"],
        )
        @command_handler(CreateUserCommand)
        async def handle_create_user(command: CreateUserCommand) -> str:
            return await user_service.create(command)
        ```
    """

    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            # Find the command argument
            command = None
            for arg in args:
                if hasattr(type(arg), "model_fields") or hasattr(
                    type(arg), "__dataclass_fields__"
                ):  # Pydantic model
                    command = arg
                    break

            if command is None:
                for kwarg in kwargs.values():
                    if hasattr(type(kwarg), "model_fields") or hasattr(
                        type(kwarg), "__dataclass_fields__"
                    ):
                        command = kwarg
                        break

            if command:
                _validate_command_fields(
                    command,
                    max_length,
                    required_fields,
                    custom_validators,
                )

            return await cast("Any", func)(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            command = None
            for arg in args:
                if hasattr(type(arg), "model_fields") or hasattr(
                    type(arg), "__dataclass_fields__"
                ):
                    command = arg
                    break

            if command is None:
                for kwarg in kwargs.values():
                    if hasattr(type(kwarg), "model_fields") or hasattr(
                        type(kwarg), "__dataclass_fields__"
                    ):
                        command = kwarg
                        break

            if command:
                _validate_command_fields(
                    command,
                    max_length,
                    required_fields,
                    custom_validators,
                )

            return func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return cast("Callable[P, Any]", async_wrapper)
        return cast("Callable[P, Any]", sync_wrapper)

    return decorator


def _validate_command_fields(
    command: Any,
    max_length: dict[str, int] | None,
    required_fields: list[str] | None,
    custom_validators: list[Callable] | None,
) -> None:
    """Validate command fields based on specified rules."""
    errors: list[str] = []

    # Check required fields
    if required_fields:
        for field in required_fields:
            value = getattr(command, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Field '{field}' is required")

    # Check max length
    if max_length:
        for field, max_len in max_length.items():
            value = getattr(command, field, None)
            if value is not None and isinstance(value, str) and len(value) > max_len:
                errors.append(f"Field '{field}' exceeds maximum length of {max_len}")

    # Run custom validators
    if custom_validators:
        for validator in custom_validators:
            try:
                validator(command)
            except (ValueError, TypeError, AttributeError, RuntimeError) as e:
                errors.append(str(e))

    if errors:
        raise CQRSValidationError(
            f"Command validation failed: {'; '.join(errors)}",
            errors=[{"field": "", "msg": e} for e in errors],  # type: ignore[misc]
        )


def validate_query(
    *,
    max_results: int | None = None,
    allowed_sort_fields: list[str] | None = None,
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """Decorator to add validation rules to query handlers.

    Args:
        max_results: Maximum allowed results per query.
        allowed_sort_fields: List of allowed sort fields.

    Returns:
        Decorator function.

    Example:
        ```python
        @validate_query(max_results=100, allowed_sort_fields=["created_at", "name"])
        @query_handler(ListUsersQuery)
        async def handle_list_users(query: ListUsersQuery) -> list[UserDTO]:
            return await user_repository.list(query)
        ```
    """

    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            query = None
            for arg in args:
                if hasattr(type(arg), "model_fields") or hasattr(
                    type(arg), "__dataclass_fields__"
                ):
                    query = arg
                    break

            if query is None:
                for kwarg in kwargs.values():
                    if hasattr(type(kwarg), "model_fields") or hasattr(
                        type(kwarg), "__dataclass_fields__"
                    ):
                        query = kwarg
                        break

            if query:
                _validate_query_fields(query, max_results, allowed_sort_fields)

            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            query = None
            for arg in args:
                if hasattr(type(arg), "model_fields") or hasattr(
                    type(arg), "__dataclass_fields__"
                ):
                    query = arg
                    break

            if query is None:
                for kwarg in kwargs.values():
                    if hasattr(type(kwarg), "model_fields") or hasattr(
                        type(kwarg), "__dataclass_fields__"
                    ):
                        query = kwarg
                        break

            if query:
                _validate_query_fields(query, max_results, allowed_sort_fields)

            return func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return cast("Callable[P, Any]", async_wrapper)
        return cast("Callable[P, Any]", sync_wrapper)

    return decorator


def _validate_query_fields(
    query: Any,
    max_results: int | None,
    allowed_sort_fields: list[str] | None,
) -> None:
    """Validate query fields based on specified rules."""
    errors: list[str] = []

    # Check limit/page_size against max_results
    if max_results:
        limit = getattr(query, "limit", None) or getattr(query, "page_size", None)
        if limit is not None and limit > max_results:
            errors.append(f"Requested limit {limit} exceeds maximum of {max_results}")

    # Check sort field against allowed list
    if allowed_sort_fields:
        sort_by = getattr(query, "sort_by", None) or getattr(query, "order_by", None)
        if sort_by and sort_by not in allowed_sort_fields:
            errors.append(
                f"Sort field '{sort_by}' not allowed. "
                f"Allowed: {', '.join(allowed_sort_fields)}",
            )

    if errors:
        raise CQRSValidationError(
            f"Query validation failed: {'; '.join(errors)}",
            errors=[{"field": "", "msg": e} for e in errors],  # type: ignore[misc]
        )


def idempotent(
    *,
    key_func: Callable[[Any], str] | None = None,
    ttl: int = 3600,
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """Decorator to make command handlers idempotent.

    Uses a cache to prevent duplicate processing of commands with the same key.

    Args:
        key_func: Function to extract idempotency key from command.
            If None, uses the command's idempotency_key attribute.
        ttl: Time-to-live for cached results in seconds.

    Returns:
        Decorator function.

    Example:
        ```python
        @idempotent(key_func=lambda cmd: cmd.request_id)
        @command_handler(ProcessPaymentCommand)
        async def handle_payment(command: ProcessPaymentCommand) -> str:
            # Only executed once per request_id
            return await payment_service.process(command)
        ```
    """

    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            # Find the command
            command = None
            for arg in args:
                if hasattr(type(arg), "model_fields") or hasattr(
                    type(arg), "__dataclass_fields__"
                ):
                    command = arg
                    break

            if command is None:
                for kwarg in kwargs.values():
                    if hasattr(type(kwarg), "model_fields") or hasattr(
                        type(kwarg), "__dataclass_fields__"
                    ):
                        command = kwarg
                        break

            if command is None:
                return await cast("Any", func)(*args, **kwargs)

            # Get idempotency key
            key: Any
            if key_func:
                key = key_func(command)
            else:
                key = getattr(command, "idempotency_key", None)
                if key is None:
                    # Generate key from command content
                    if hasattr(command, "model_dump_json"):
                        content = command.model_dump_json()
                    else:
                        content = str(command)
                    key = hashing.hash_hex(content)

            cache_key = f"idempotent:{type(command).__name__}:{key}"

            # Check cache
            if cache_key in _idempotency_cache:
                return _idempotency_cache[cache_key]

            # Execute and cache
            result = await cast("Any", func)(*args, **kwargs)
            _idempotency_cache[cache_key] = result

            return result

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            command = None
            for arg in args:
                if hasattr(type(arg), "model_fields") or hasattr(
                    type(arg), "__dataclass_fields__"
                ):
                    command = arg
                    break

            if command is None:
                for kwarg in kwargs.values():
                    if hasattr(type(kwarg), "model_fields") or hasattr(
                        type(kwarg), "__dataclass_fields__"
                    ):
                        command = kwarg
                        break

            if command is None:
                return func(*args, **kwargs)

            key: Any
            if key_func:
                key = key_func(command)
            else:
                key = getattr(command, "idempotency_key", None)
                if key is None:
                    if hasattr(command, "model_dump_json"):
                        content = command.model_dump_json()
                    else:
                        content = str(command)
                    key = hashing.hash_hex(content)
            cache_key = f"idempotent:{type(command).__name__}:{key}"

            if cache_key in _idempotency_cache:
                return _idempotency_cache[cache_key]

            result = func(*args, **kwargs)
            _idempotency_cache[cache_key] = result

            return result

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return cast("Callable[P, Any]", async_wrapper)
        return cast("Callable[P, Any]", sync_wrapper)

    return decorator


def clear_idempotency_cache() -> None:
    """Clear the idempotency cache.

    Useful for testing or when cache needs to be reset.
    """
    _idempotency_cache.clear()
