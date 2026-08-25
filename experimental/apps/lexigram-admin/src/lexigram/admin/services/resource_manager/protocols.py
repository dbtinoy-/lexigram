"""Protocols and default implementations for the resource manager.

Defines the data-source, validator, and authorizer contracts consumed by
:class:`~lexigram.admin.services.resource_manager.ResourceManager`, plus the
permissive default implementations used when none are supplied.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable

from lexigram.admin.data.paged_result import PagedResult
from lexigram.admin.data.query import QuerySpec
from lexigram.admin.exceptions import AdminDataError, AdminValidationError
from lexigram.result import Ok, Result

T = TypeVar("T")


@runtime_checkable
class ResourceDataSourceProtocol(Protocol[T]):
    """Protocol for data access operations."""

    async def find_many(self, query: QuerySpec) -> PagedResult[T]: ...

    async def find_one(self, item_id: Any) -> T | None: ...

    async def create(self, data: dict[str, Any]) -> T: ...

    async def update(self, item_id: Any, data: dict[str, Any]) -> T: ...

    async def delete(self, item_id: Any) -> bool: ...


@runtime_checkable
class ResultDataSource(Protocol[T]):
    """Enhanced protocol for data access operations that return Results.

    This is the idiomatic pattern for new implementations.
    Existing ResourceDataSourceProtocol implementations can be wrapped or gradually migrated
    to this protocol.
    """

    async def find_many(
        self, query: QuerySpec
    ) -> Result[PagedResult[T], AdminDataError]: ...

    async def find_one(self, item_id: Any) -> Result[T, AdminDataError]: ...

    async def create(self, data: dict[str, Any]) -> Result[T, AdminDataError]: ...

    async def update(
        self, item_id: Any, data: dict[str, Any]
    ) -> Result[T, AdminDataError]: ...

    async def delete(self, item_id: Any) -> Result[bool, AdminDataError]: ...


@runtime_checkable
class Validator(Protocol):
    """Protocol for data validation."""

    async def validate(
        self,
        data: dict[str, Any],
    ) -> Result[dict[str, Any], AdminValidationError]: ...


class DefaultValidator:
    """Default validator that accepts all data."""

    async def validate(
        self,
        data: dict[str, Any],
    ) -> Result[dict[str, Any], AdminValidationError]:
        return Ok(data)


class DefaultAuthorizer:
    """Default authorizer that allows all operations."""

    async def can_view(
        self,
        user: Any,
        resource: str,
        record: Any = None,
    ) -> bool:
        return True

    async def can_create(
        self,
        user: Any,
        resource: str,
    ) -> bool:
        return True

    async def can_update(
        self,
        user: Any,
        resource: str,
        record: Any = None,
    ) -> bool:
        return True

    async def can_delete(
        self,
        user: Any,
        resource: str,
        record: Any = None,
    ) -> bool:
        return True

    async def can_execute_action(
        self,
        user: Any,
        resource: str,
        action: str,
        record: Any | None = None,
    ) -> bool:
        return True


__all__ = [
    "DefaultAuthorizer",
    "DefaultValidator",
    "ResourceDataSourceProtocol",
    "ResultDataSource",
    "Validator",
]
