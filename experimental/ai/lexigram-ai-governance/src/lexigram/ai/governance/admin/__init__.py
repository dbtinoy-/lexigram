"""Admin dashboard contribution for AI governance.

The contributor surfaces relay usage, quota pressure, and settlement
failures as dashboard widgets, health checks, and management pages.
"""

from __future__ import annotations

from lexigram.ai.governance.admin.contributor import (
    PERMISSION_LEDGER,
    PERMISSION_READ,
    GovernanceAdminContributor,
)
from lexigram.ai.governance.admin.pages import (
    GovernanceQuotasPage,
    GovernanceRelayUsagePage,
    GovernanceSettlementsPage,
)

__all__ = [
    "PERMISSION_LEDGER",
    "PERMISSION_READ",
    "GovernanceAdminContributor",
    "GovernanceQuotasPage",
    "GovernanceRelayUsagePage",
    "GovernanceSettlementsPage",
]
