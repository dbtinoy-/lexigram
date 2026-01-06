"""Internal exception wrappers for lexigram-tenancy.

These re-export the contract exceptions and may be extended with
package-specific context in the future.
"""

from __future__ import annotations

from lexigram.contracts.tenancy.errors import (
    TenantConfigError,
    TenantError,
    TenantInactiveError,
    TenantNotFoundError,
    TenantProvisioningError,
    TenantResolutionError,
    TenantSlugConflictError,
    TenantSuspendedError,
)

__all__ = [
    "TenantConfigError",
    "TenantError",
    "TenantInactiveError",
    "TenantNotFoundError",
    "TenantProvisioningError",
    "TenantResolutionError",
    "TenantSlugConflictError",
    "TenantSuspendedError",
]
