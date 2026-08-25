"""Resource manager for orchestrating CRUD with validation and authorization.

This package provides the ResourceManager class that coordinates data access,
validation, and authorization using the Result type for explicit error handling.

SVC-01: ResourceManager implementation.
"""

from __future__ import annotations

from lexigram.admin.services.resource_manager.adapter import (
    find_many_safe as find_many_safe,
)
from lexigram.admin.services.resource_manager.adapter import (
    find_one_safe as find_one_safe,
)
from lexigram.admin.services.resource_manager.adapter import (
    is_result_data_source as is_result_data_source,
)
from lexigram.admin.services.resource_manager.audit import (
    record_audit as record_audit,
)
from lexigram.admin.services.resource_manager.manager import (
    ResourceManager as ResourceManager,
)
from lexigram.admin.services.resource_manager.protocols import (
    DefaultAuthorizer as DefaultAuthorizer,
)
from lexigram.admin.services.resource_manager.protocols import (
    DefaultValidator as DefaultValidator,
)
from lexigram.admin.services.resource_manager.protocols import (
    ResourceDataSourceProtocol as ResourceDataSourceProtocol,
)
from lexigram.admin.services.resource_manager.protocols import (
    ResultDataSource as ResultDataSource,
)
from lexigram.admin.services.resource_manager.protocols import (
    Validator as Validator,
)

__all__ = [
    "DefaultAuthorizer",
    "DefaultValidator",
    "ResourceDataSourceProtocol",
    "ResourceManager",
    "ResultDataSource",
    "Validator",
    "find_many_safe",
    "find_one_safe",
    "is_result_data_source",
    "record_audit",
]
