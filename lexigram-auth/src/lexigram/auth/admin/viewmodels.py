"""Frozen viewmodels for auth admin widgets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActiveSessionsViewModel:
    """Data model for active sessions widget."""

    count: int
    peak_today: int


@dataclass(frozen=True)
class TokenRefreshRateViewModel:
    """Data model for token refresh rate widget."""

    refreshes_per_minute: float
    total_refreshes: int


@dataclass(frozen=True)
class FailedLoginsViewModel:
    """Data model for failed logins widget."""

    count: int
    unique_ips: int
    is_elevated: bool  # True if above threshold


__all__ = [
    "ActiveSessionsViewModel",
    "FailedLoginsViewModel",
    "TokenRefreshRateViewModel",
]
