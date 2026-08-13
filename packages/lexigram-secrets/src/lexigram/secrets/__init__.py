"""Secret vaults with rotation, tenant scoping, and audit.

Provides ``RotatableSecretStoreProtocol``, versioned rotation,
tenant isolation, audit logging, and a conformance test suite.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING, Any

from lexigram.secrets.constants import __version__ as __version__

__path__ = pkgutil.extend_path(__path__, __name__)

if TYPE_CHECKING:
    from lexigram.secrets.config import SecretsConfig
    from lexigram.secrets.events import (
        SecretAccessedEvent,
        SecretCreatedEvent,
        SecretDeletedEvent,
        SecretRotatedEvent,
    )
    from lexigram.secrets.exceptions import (
        SecretAccessError,
        SecretBackendError,
        SecretConfigError,
        SecretNotFoundError,
        SecretRotationError,
        SecretsError,
    )
    from lexigram.secrets.hooks import (
        SecretAccessedHook,
        SecretCreatedHook,
        SecretDeletedHook,
        SecretRotatedHook,
    )
    from lexigram.secrets.module import SecretsModule
    from lexigram.secrets.protocols import (
        AsyncSecretStoreProtocol,
        RotatableSecretStoreProtocol,
    )
    from lexigram.secrets.types import SecretVersion, VersionedSecret

_LAZY_IMPORTS: dict[str, str] = {
    "AsyncSecretStoreProtocol": "lexigram.secrets.protocols",
    "RotatableSecretStoreProtocol": "lexigram.secrets.protocols",
    "RotationDecorator": "lexigram.secrets.rotation",
    "RotationSchedule": "lexigram.secrets.rotation",
    "SecretAccessError": "lexigram.secrets.exceptions",
    "SecretAccessedEvent": "lexigram.secrets.events",
    "SecretAccessedHook": "lexigram.secrets.hooks",
    "SecretAuditDecorator": "lexigram.secrets.audit",
    "SecretBackendError": "lexigram.secrets.exceptions",
    "SecretConfigError": "lexigram.secrets.exceptions",
    "SecretCreatedEvent": "lexigram.secrets.events",
    "SecretCreatedHook": "lexigram.secrets.hooks",
    "SecretDeletedEvent": "lexigram.secrets.events",
    "SecretDeletedHook": "lexigram.secrets.hooks",
    "SecretNotFoundError": "lexigram.secrets.exceptions",
    "SecretRotatedEvent": "lexigram.secrets.events",
    "SecretRotatedHook": "lexigram.secrets.hooks",
    "SecretRotationError": "lexigram.secrets.exceptions",
    "SecretVersion": "lexigram.secrets.types",
    "SecretsConfig": "lexigram.secrets.config",
    "SecretsError": "lexigram.secrets.exceptions",
    "SecretsModule": "lexigram.secrets.module",
    "TenantScopedSecretStore": "lexigram.secrets.tenancy",
    "VersionedSecret": "lexigram.secrets.types",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        module_path = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__} has no attribute {name}")


def __dir__() -> list[str]:
    return [*list(_LAZY_IMPORTS.keys()), "__version__"]


__all__ = [
    "AsyncSecretStoreProtocol",
    "RotatableSecretStoreProtocol",
    "RotationDecorator",
    "RotationSchedule",
    "SecretAccessError",
    "SecretAccessedEvent",
    "SecretAccessedHook",
    "SecretAuditDecorator",
    "SecretBackendError",
    "SecretConfigError",
    "SecretCreatedEvent",
    "SecretCreatedHook",
    "SecretDeletedEvent",
    "SecretDeletedHook",
    "SecretNotFoundError",
    "SecretRotatedEvent",
    "SecretRotatedHook",
    "SecretRotationError",
    "SecretVersion",
    "SecretsConfig",
    "SecretsError",
    "SecretsModule",
    "TenantScopedSecretStore",
    "VersionedSecret",
    "__version__",
]
