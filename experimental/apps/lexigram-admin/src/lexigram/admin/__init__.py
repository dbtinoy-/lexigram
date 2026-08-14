"""Lexigram Admin — Administrative panel for Lexigram applications."""

from __future__ import annotations

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

import importlib.metadata
from typing import TYPE_CHECKING, Any

from lexigram.admin.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.admin.contributors.base import BaseAdminContributor
    from lexigram.admin.contributors.core import CoreAdminContributor
    from lexigram.admin.contributors.registry import ContributorRegistry
    from lexigram.admin.di.bundle_provider import AdminProvider
    from lexigram.admin.exceptions import (
        AdminError,
        AdminValidationError,
        ConflictError,
        DataError,
        ErrorCode,
        NotFoundError,
        NotificationError,
        PermissionDeniedError,
    )
    from lexigram.admin.module import AdminModule
    from lexigram.admin.types import AdminStatus, AdminUser
    from lexigram.contracts.admin.protocols import (
        AdminContributorProtocol,
        AdminContributorRegistryProtocol,
        AdminDashboardProtocol,
    )

_LAZY_IMPORTS: dict[str, str] = {
    # Exceptions
    "AdminError": "lexigram.admin.exceptions",
    "AdminValidationError": "lexigram.admin.exceptions",
    "ConflictError": "lexigram.admin.exceptions",
    "DataError": "lexigram.admin.exceptions",
    "ErrorCode": "lexigram.admin.exceptions",
    "NotFoundError": "lexigram.admin.exceptions",
    "NotificationError": "lexigram.admin.exceptions",
    "PermissionDeniedError": "lexigram.admin.exceptions",
    # DI
    "AdminProvider": "lexigram.admin.di.bundle_provider",
    "AdminModule": "lexigram.admin.module",
    # Contributors
    "BaseAdminContributor": "lexigram.admin.contributors.base",
    "CoreAdminContributor": "lexigram.admin.contributors.core",
    "ContributorRegistry": "lexigram.admin.contributors.registry",
    # Protocols (canonical locations in lexigram-contracts)
    "AdminContributorProtocol": "lexigram.contracts.admin.protocols",
    "AdminContributorRegistryProtocol": "lexigram.contracts.admin.protocols",
    "AdminDashboardProtocol": "lexigram.contracts.admin.protocols",
    # Types
    "AdminStatus": "lexigram.admin.types",
    "AdminUser": "lexigram.admin.types",
    # Hooks
    "AdminPanelStartedHook": "lexigram.admin.hooks",
    "AdminPanelStoppedHook": "lexigram.admin.hooks",
    "AdminResourceAccessedHook": "lexigram.admin.hooks",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "AdminContributorProtocol",
    "AdminContributorRegistryProtocol",
    "AdminDashboardProtocol",
    "AdminError",
    "AdminModule",
    "AdminPanelStartedHook",
    "AdminPanelStoppedHook",
    "AdminProvider",
    "AdminResourceAccessedHook",
    "AdminStatus",
    "AdminUser",
    "AdminValidationError",
    "BaseAdminContributor",
    "ConflictError",
    "ContributorRegistry",
    "CoreAdminContributor",
    "DataError",
    "ErrorCode",
    "NotFoundError",
    "NotificationError",
    "PermissionDeniedError",
]
