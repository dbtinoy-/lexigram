"""Testing Domain - Authentication Testing Infrastructure"""

from __future__ import annotations

from lexigram.testing.clients.auth.bed import AuthTestBed
from lexigram.testing.clients.auth.client import AuthTestClient
from lexigram.testing.clients.auth.fixtures import (
    admin_request_context,
    admin_token,
    auth_headers_factory,
    auth_test_bed,
    auth_test_client,
    created_test_user_admin,
    created_test_user_moderator,
    created_test_user_regular,
    expired_token,
    invalid_token,
    mock_auth_provider,
    mock_token_manager,
    mock_user_store,
    moderator_request_context,
    moderator_token,
    multiple_test_users,
    multiple_user_tokens,
    test_user_admin,
    test_user_inactive,
    test_user_moderator,
    test_user_regular,
    test_user_unverified,
    user_request_context,
    user_token,
)
from lexigram.testing.clients.auth.types import AuthTestToken, AuthTestUser

__all__ = [
    "AuthTestBed",
    "AuthTestClient",
    "AuthTestToken",
    "AuthTestUser",
    "admin_request_context",
    "admin_token",
    "auth_headers_factory",
    "auth_test_bed",
    "auth_test_client",
    "created_test_user_admin",
    "created_test_user_moderator",
    "created_test_user_regular",
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
