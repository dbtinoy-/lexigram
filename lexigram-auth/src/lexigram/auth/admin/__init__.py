"""Admin dashboard widgets and contributor for lexigram-auth."""

from __future__ import annotations

from lexigram.auth.admin.contributor import AuthAdminContributor
from lexigram.auth.admin.handlers import (
    ActiveSessionsWidgetHandler,
    FailedLoginsWidgetHandler,
    TokenRefreshRateWidgetHandler,
)
from lexigram.auth.admin.viewmodels import (
    ActiveSessionsViewModel,
    FailedLoginsViewModel,
    TokenRefreshRateViewModel,
)

__all__ = [
    "ActiveSessionsViewModel",
    "ActiveSessionsWidgetHandler",
    "AuthAdminContributor",
    "FailedLoginsViewModel",
    "FailedLoginsWidgetHandler",
    "TokenRefreshRateViewModel",
    "TokenRefreshRateWidgetHandler",
]
