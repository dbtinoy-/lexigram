"""Domain package exports.

Re-exports all public domain types so consumers can import from
``lexigram_example_platform.domain`` instead of sub-modules.
"""

from __future__ import annotations

from lexigram_example_platform.domain.membership import (
    Membership,
    Role,
    RoleChanged,
    UserInvited,
)
from lexigram_example_platform.domain.policy import can_access
from lexigram_example_platform.domain.tenant import (
    Tenant,
    TenantCreated,
    TenantStatus,
    TenantSuspended,
)

__all__ = [
    "Membership",
    "Role",
    "RoleChanged",
    "Tenant",
    "TenantCreated",
    "TenantStatus",
    "TenantSuspended",
    "UserInvited",
    "can_access",
]
