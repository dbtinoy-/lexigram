"""Admin management pages for lexigram-auth."""

from __future__ import annotations

from lexigram.auth.admin.pages.overview import AuthOverviewPage
from lexigram.auth.admin.pages.sessions import AuthSessionsPage
from lexigram.auth.admin.pages.tokens import AuthTokensPage
from lexigram.auth.admin.pages.users import AuthUsersPage

__all__ = [
    "AuthOverviewPage",
    "AuthSessionsPage",
    "AuthTokensPage",
    "AuthUsersPage",
]
