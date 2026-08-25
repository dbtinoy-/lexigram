"""ResourceManager: CRUD orchestration with validation and authorization.

SVC-01: coordinates data access (via the safe adapters in
:mod:`lexigram.admin.services.resource_manager.adapter`), input validation,
and authorization using the Result type for explicit error handling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from lexigram.admin.data.paged_result import PagedResult
from lexigram.admin.data.query import QuerySpec
from lexigram.admin.exceptions import (
    AdminDataError,
    AdminValidationError,
    NotFoundError,
)
from lexigram.admin.services.resource_manager.adapter import (
    find_many_safe,
    find_one_safe,
)
from lexigram.admin.services.resource_manager.audit import record_audit
from lexigram.admin.services.resource_manager.protocols import (
    DefaultAuthorizer,
    DefaultValidator,
    ResourceDataSourceProtocol,
    Validator,
)
from lexigram.contracts.audit import AuditEventSeverity, AuditLoggerProtocol
from lexigram.contracts.auth import AuthorizerProtocol
from lexigram.contracts.exceptions import PermissionDeniedError as PermissionDenied
from lexigram.di.decorators import inject
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.data.sql.unit_of_work import UnitOfWorkProtocol

T = TypeVar("T")


@inject
class ResourceManager(Generic[T]):
    """Orchestrates CRUD operations with validation and authorization.

    ResourceManager provides a high-level interface for resource operations
    that combines:
    - Data access through ResourceDataSourceProtocol protocol
    - Input validation through Validator protocol
    - Authorization through AuthorizerProtocol protocol

    All operations return Result types for explicit error handling without
    exceptions.

    Example:
        >>> manager = ResourceManager(
        ...     resource_name="users",
        ...     data_source=user_data_source,
        ...     validator=user_validator,
        ...     authorizer=role_authorizer,
        ... )
        >>> result = await manager.list(query, user=current_user)
        >>> if result.is_ok():
        ...     users = result.unwrap()
        ... else:
        ...     error = result.unwrap_err()
    """

    def __init__(
        self,
        resource_name: str,
        data_source: ResourceDataSourceProtocol[T],
        validator: Validator | None = None,
        authorizer: AuthorizerProtocol | None = None,
        model: type[T] | None = None,
        uow: UnitOfWorkProtocol | None = None,
        audit: AuditLoggerProtocol | None = None,
    ):
        """Initialize the resource manager.

        Args:
            resource_name: Name of the resource (for authorization/display)
            data_source: Data source for CRUD operations
            validator: Optional validator for input validation
            authorizer: Optional authorizer for access control
            model: Optional model class for typing results
            uow: Optional unit-of-work for transactional bulk operations
            audit: Optional audit logger for recording operations
        """
        self.resource_name = resource_name
        self.data_source = data_source
        self.validator = validator or DefaultValidator()
        self.authorizer = authorizer or DefaultAuthorizer()
        self.model = model
        self._uow = uow
        self._audit = audit

    async def list(
        self,
        query: QuerySpec,
        *,
        user: Any = None,
    ) -> Result[PagedResult[T], PermissionDenied | AdminDataError]:
        """List resources with authorization check.

        Args:
            query: Query specification for filtering/pagination
            user: Current user for authorization

        Returns:
            Result containing PagedResult on success, error on failure
        """
        if not await self.authorizer.can_view(user, self.resource_name):
            return Err(
                PermissionDenied(
                    resource=self.resource_name,
                    action="view",
                    message=f"Cannot view {self.resource_name}",
                ),
            )

        # Use safe wrapper that handles both ResourceDataSourceProtocol and ResultDataSource
        find_result = await find_many_safe(self.data_source, self.resource_name, query)
        if find_result.is_err():
            return Err(find_result.unwrap_err())

        result = find_result.unwrap()

        # Convert to PagedResult and transform to model if specified
        paged = PagedResult(
            items=result.items,
            total=result.total,
            page=result.page,
            per_page=result.per_page,
            cursor=getattr(result, "cursor", None),
        )

        if self.model:
            paged = paged.map(lambda x: self.model(**x) if isinstance(x, dict) else x)

        return Ok(paged)

    async def get(
        self,
        item_id: Any,
        *,
        user: Any = None,
    ) -> Result[T, PermissionDenied | NotFoundError | AdminDataError]:
        """Get a single resource by ID.

        Args:
            item_id: Resource identifier
            user: Current user for authorization

        Returns:
            Result containing resource on success, error on failure
        """
        # Use safe wrapper that handles both ResourceDataSourceProtocol and ResultDataSource
        find_result = await find_one_safe(self.data_source, self.resource_name, item_id)
        if find_result.is_err():
            return Err(find_result.unwrap_err())

        record = find_result.unwrap()

        if record is None:
            return Err(
                NotFoundError(
                    resource=self.resource_name,
                    identifier=str(item_id),
                    message=f"{self.resource_name} not found",
                ),
            )

        if not await self.authorizer.can_view(user, self.resource_name, record):
            return Err(
                PermissionDenied(
                    resource=self.resource_name,
                    action="view",
                    message=f"Cannot view this {self.resource_name}",
                ),
            )

        if self.model and isinstance(record, dict):
            record = self.model(**record)

        return Ok(record)

    async def create(
        self,
        data: dict[str, Any],
        *,
        user: Any = None,
    ) -> Result[T, PermissionDenied | AdminValidationError]:
        """Create a new resource.

        Args:
            data: Resource data
            user: Current user for authorization

        Returns:
            Result containing created resource on success, error on failure
        """
        if not await self.authorizer.can_create(user, self.resource_name):
            return Err(
                PermissionDenied(
                    resource=self.resource_name,
                    action="create",
                    message=f"Cannot create {self.resource_name}",
                ),
            )

        # Validate data
        validation_result = await self.validator.validate(data)
        if validation_result.is_err():
            return validation_result  # type: ignore[return-value]

        validated_data = validation_result.unwrap()
        record = await self.data_source.create(validated_data)

        if self.model and isinstance(record, dict):
            record = self.model(**record)

        # Record successful creation audit event
        resource_id = getattr(record, "id", str(record))
        await record_audit(
            self._audit,
            self.resource_name,
            action="admin.resource.create",
            actor=user,
            resource_id=resource_id,
            outcome="success",
            severity=AuditEventSeverity.MEDIUM,
        )

        return Ok(record)

    async def update(
        self,
        item_id: Any,
        data: dict[str, Any],
        *,
        user: Any = None,
    ) -> Result[T, PermissionDenied | AdminValidationError | NotFoundError]:
        """Update an existing resource.

        Args:
            item_id: Resource identifier
            data: Update data
            user: Current user for authorization

        Returns:
            Result containing updated resource on success, error on failure
        """
        # Check if record exists
        record = await self.data_source.find_one(item_id)
        if record is None:
            return Err(
                NotFoundError(
                    resource=self.resource_name,
                    identifier=str(item_id),
                    message=f"{self.resource_name} not found",
                ),
            )

        # Check authorization
        if not await self.authorizer.can_update(user, self.resource_name, record):
            return Err(
                PermissionDenied(
                    resource=self.resource_name,
                    action="update",
                    message=f"Cannot update this {self.resource_name}",
                ),
            )

        # Validate data
        validation_result = await self.validator.validate(data)
        if validation_result.is_err():
            return validation_result  # type: ignore[return-value]

        validated_data = validation_result.unwrap()
        updated = await self.data_source.update(item_id, validated_data)

        if self.model and isinstance(updated, dict):
            updated = self.model(**updated)

        # Record successful update audit event
        resource_id = getattr(updated, "id", str(item_id))
        await record_audit(
            self._audit,
            self.resource_name,
            action="admin.resource.update",
            actor=user,
            resource_id=resource_id,
            outcome="success",
            severity=AuditEventSeverity.MEDIUM,
        )

        return Ok(updated)

    async def _delete_internal(
        self,
        item_id: Any,
        user: Any = None,
        *,
        skip_audit: bool = False,
    ) -> Result[bool, PermissionDenied | NotFoundError]:
        """Internal delete implementation shared by delete() and bulk_delete().

        Args:
            item_id: Resource identifier
            user: Current user for authorization
            skip_audit: If True, skip audit recording (used by bulk_delete fallback)

        Returns:
            Result containing True on success, error on failure
        """
        # Check if record exists
        record = await self.data_source.find_one(item_id)
        if record is None:
            return Err(
                NotFoundError(
                    resource=self.resource_name,
                    identifier=str(item_id),
                    message=f"{self.resource_name} not found",
                ),
            )

        # Check authorization
        if not await self.authorizer.can_delete(user, self.resource_name, record):
            return Err(
                PermissionDenied(
                    resource=self.resource_name,
                    action="delete",
                    message=f"Cannot delete this {self.resource_name}",
                ),
            )

        await self.data_source.delete(item_id)

        # Record successful deletion audit event unless skipped (bulk_delete handles its own audit)
        if not skip_audit:
            await record_audit(
                self._audit,
                self.resource_name,
                action="admin.resource.delete",
                actor=user,
                resource_id=str(item_id),
                outcome="success",
                severity=AuditEventSeverity.CRITICAL,
            )

        return Ok(True)

    async def delete(
        self,
        item_id: Any,
        *,
        user: Any = None,
    ) -> Result[bool, PermissionDenied | NotFoundError]:
        """Delete a resource.

        Args:
            item_id: Resource identifier
            user: Current user for authorization

        Returns:
            Result containing True on success, error on failure
        """
        return await self._delete_internal(item_id, user)

    async def bulk_delete(
        self,
        ids: list[Any],  # type: ignore[valid-type]
        *,
        user: Any = None,
    ) -> Result[int, PermissionDenied]:
        """Delete multiple resources.

        Args:
            ids: List of resource identifiers
            user: Current user for authorization

        Returns:
            Result containing count of deleted resources, error on failure
        """
        # Check bulk authorization
        if not await self.authorizer.can_delete(user, self.resource_name):
            return Err(
                PermissionDenied(
                    resource=self.resource_name,
                    action="delete",
                    message=f"Cannot delete {self.resource_name}",
                ),
            )

        # Check ResourceDataSourceProtocol supports bulk operations
        if hasattr(self.data_source, "delete_many"):
            count = await self.data_source.delete_many(ids)
        else:
            # Fallback to individual deletes without per-item audit events
            count = 0
            if self._uow is not None:
                async with self._uow:
                    for id_ in ids:  # type: ignore[attr-defined]
                        result = await self._delete_internal(
                            id_, user=user, skip_audit=True
                        )
                        if result.is_ok():
                            count += 1
            else:
                for id_ in ids:  # type: ignore[attr-defined]
                    result = await self._delete_internal(
                        id_, user=user, skip_audit=True
                    )
                    if result.is_ok():
                        count += 1

        # Record single bulk deletion audit event for both paths
        await record_audit(
            self._audit,
            self.resource_name,
            action="admin.resource.bulk_delete",
            actor=user,
            resource_id="bulk",
            outcome="success",
            severity=AuditEventSeverity.CRITICAL,
            deleted_count=count,
            requested_ids=len(ids),
        )

        return Ok(count)

    async def bulk_update(
        self,
        updates: list[tuple[Any, dict[str, Any]]],  # type: ignore[valid-type]
        *,
        user: Any = None,
    ) -> Result[int, PermissionDenied]:
        """Update multiple resources.

        Args:
            updates: List of (id, data) tuples
            user: Current user for authorization

        Returns:
            Result containing count of updated resources, error on failure
        """
        # Check bulk authorization
        if not await self.authorizer.can_update(user, self.resource_name):
            return Err(
                PermissionDenied(
                    resource=self.resource_name,
                    action="update",
                    message=f"Cannot update {self.resource_name}",
                ),
            )

        # Check ResourceDataSourceProtocol supports bulk operations
        if hasattr(self.data_source, "update_many"):
            count = await self.data_source.update_many(updates)
            return Ok(count)

        # Fallback to individual updates
        count = 0
        if self._uow is not None:
            async with self._uow:
                for id_, data in updates:  # type: ignore[attr-defined]
                    result = await self.update(id_, data, user=user)
                    if result.is_ok():
                        count += 1
        else:
            for id_, data in updates:  # type: ignore[attr-defined]
                result = await self.update(id_, data, user=user)
                if result.is_ok():
                    count += 1

        return Ok(count)


__all__ = ["ResourceManager"]
