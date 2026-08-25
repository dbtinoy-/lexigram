"""Pytest fixtures for lexigram-auth testing.

This package provides comprehensive pytest fixtures for testing lexigram-auth
functionality, integrating with the lexigram.testing infrastructure. Concerns
are grouped into submodules — ``beds`` (test bed and client), ``users`` (user
templates, created users, bulk users), ``tokens`` (tokens and authorized
request contexts), and ``mocks`` (unit-test doubles) — and re-exported here.
"""

from __future__ import annotations

from lexigram.testing.clients.auth.bed import AuthTestBed as AuthTestBed
from lexigram.testing.clients.auth.client import AuthTestClient as AuthTestClient
from lexigram.testing.clients.auth.fixtures._async import (
    async_fixture as async_fixture,
)
from lexigram.testing.clients.auth.fixtures.beds import (
    auth_test_bed as auth_test_bed,
)
from lexigram.testing.clients.auth.fixtures.beds import (
    auth_test_client as auth_test_client,
)
from lexigram.testing.clients.auth.fixtures.mocks import (
    mock_auth_provider as mock_auth_provider,
)
from lexigram.testing.clients.auth.fixtures.mocks import (
    mock_token_manager as mock_token_manager,
)
from lexigram.testing.clients.auth.fixtures.mocks import (
    mock_user_store as mock_user_store,
)
from lexigram.testing.clients.auth.fixtures.tokens import (
    admin_request_context as admin_request_context,
)
from lexigram.testing.clients.auth.fixtures.tokens import (
    admin_token as admin_token,
)
from lexigram.testing.clients.auth.fixtures.tokens import (
    auth_headers_factory as auth_headers_factory,
)
from lexigram.testing.clients.auth.fixtures.tokens import (
    expired_token as expired_token,
)
from lexigram.testing.clients.auth.fixtures.tokens import (
    invalid_token as invalid_token,
)
from lexigram.testing.clients.auth.fixtures.tokens import (
    moderator_request_context as moderator_request_context,
)
from lexigram.testing.clients.auth.fixtures.tokens import (
    moderator_token as moderator_token,
)
from lexigram.testing.clients.auth.fixtures.tokens import (
    multiple_user_tokens as multiple_user_tokens,
)
from lexigram.testing.clients.auth.fixtures.tokens import (
    user_request_context as user_request_context,
)
from lexigram.testing.clients.auth.fixtures.tokens import (
    user_token as user_token,
)
from lexigram.testing.clients.auth.fixtures.users import (
    created_test_user_admin as created_test_user_admin,
)
from lexigram.testing.clients.auth.fixtures.users import (
    created_test_user_inactive as created_test_user_inactive,
)
from lexigram.testing.clients.auth.fixtures.users import (
    created_test_user_moderator as created_test_user_moderator,
)
from lexigram.testing.clients.auth.fixtures.users import (
    created_test_user_regular as created_test_user_regular,
)
from lexigram.testing.clients.auth.fixtures.users import (
    created_test_user_unverified as created_test_user_unverified,
)
from lexigram.testing.clients.auth.fixtures.users import (
    multiple_test_users as multiple_test_users,
)
from lexigram.testing.clients.auth.fixtures.users import (
    test_user_admin as test_user_admin,
)
from lexigram.testing.clients.auth.fixtures.users import (
    test_user_inactive as test_user_inactive,
)
from lexigram.testing.clients.auth.fixtures.users import (
    test_user_moderator as test_user_moderator,
)
from lexigram.testing.clients.auth.fixtures.users import (
    test_user_regular as test_user_regular,
)
from lexigram.testing.clients.auth.fixtures.users import (
    test_user_unverified as test_user_unverified,
)
from lexigram.testing.clients.auth.types import (
    AuthTestToken as AuthTestToken,
)
from lexigram.testing.clients.auth.types import (
    AuthTestUser as AuthTestUser,
)

__all__ = [
    "AuthTestBed",
    "AuthTestClient",
    "AuthTestToken",
    "AuthTestUser",
    "admin_request_context",
    "admin_token",
    "async_fixture",
    "auth_headers_factory",
    "auth_test_bed",
    "auth_test_client",
    "created_test_user_admin",
    "created_test_user_inactive",
    "created_test_user_moderator",
    "created_test_user_regular",
    "created_test_user_unverified",
    "expired_token",
    "invalid_token",
    "mock_auth_provider",
    "mock_token_manager",
    "mock_user_store",
    "moderator_request_context",
    "moderator_token",
    "multiple_test_users",
    "multiple_user_tokens",
    "test_user_admin",
    "test_user_inactive",
    "test_user_moderator",
    "test_user_regular",
    "test_user_unverified",
    "user_request_context",
    "user_token",
]
