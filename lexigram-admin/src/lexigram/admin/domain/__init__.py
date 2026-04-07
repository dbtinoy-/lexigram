"""Admin domain package — aggregates and specifications."""

from __future__ import annotations

from lexigram.admin.domain.aggregate import AdminUserAggregate
from lexigram.admin.domain.specifications import (
    ActiveUserSpec,
    AndSpec,
    HasRoleSpec,
    NotSpec,
    OrSpec,
    SpecificationProtocol,
)
from lexigram.admin.events import (
    BulkOperationCompleted,
    ResourceCreated,
    ResourceDeleted,
    ResourceUpdated,
    UserCreated,
    UserDeactivated,
    UserDeleted,
    UserUpdated,
)

__all__ = [
    "ActiveUserSpec",
    "AdminUserAggregate",
    "AndSpec",
    "BulkOperationCompleted",
    "HasRoleSpec",
    "NotSpec",
    "OrSpec",
    "ResourceCreated",
    "ResourceDeleted",
    "ResourceUpdated",
    "SpecificationProtocol",
    "UserCreated",
    "UserDeactivated",
    "UserDeleted",
    "UserUpdated",
]
