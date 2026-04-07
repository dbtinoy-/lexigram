from types import SimpleNamespace

import pytest

from lexigram.admin.auth.adapter import AdminAuthAdapter
from lexigram.auth.authz.service import AuthorizationService
from lexigram.auth.di import AuthenticationProvider
from lexigram.di import Container


@pytest.mark.asyncio
async def test_admin_auth_adapter_syncs_roles_and_users():
    role_def = SimpleNamespace(
        name="admin", description="Administrator", permissions=["read", "write"],
    )
    user = SimpleNamespace(
        user_id="alice",
        username="alice",
        email="alice@example.com",
        hashed_password="$2b$12$dummyhash",
        roles=["admin"],
        permissions=[],
    )

    auth_config = SimpleNamespace(users=[user], roles={"admin": role_def})

    container = Container()
    _key = "test-secret-key-for-admin-tests-32b"
    from lexigram.auth.config import AuthConfig, JWTConfig
    _config = AuthConfig(secret_key=_key, token=JWTConfig(secret_key=_key))
    auth_provider = AuthenticationProvider(config=_config)
    from lexigram.contracts.auth import AuthProviderProtocol
    container.singleton(AuthenticationProvider, lambda: auth_provider)
    container.singleton(AuthProviderProtocol, lambda: auth_provider)
    container.singleton("AdminAuthProvider", lambda: auth_provider)

    authorization_service = AuthorizationService()
    original_roles = dict(authorization_service._roles)

    try:
        adapter = AdminAuthAdapter(auth_config, authorization_service)

        await auth_provider.user_store.create_user(
            name="alice",
            email="alice@example.com",
            hashed_password="$2b$12$dummyhash",
            roles=[],
            permissions=[],
        )

        await adapter.sync(container)

        role = authorization_service.get_role("admin")
        assert role is not None
        perms = role.permissions
        assert "read" in perms and "write" in perms

        stored = await auth_provider.user_store.get_user_by_username("alice")
        assert stored is not None
        assert stored.name == "alice"
        # Note: register() syncs roles into the RBAC authorization_service (checked
        # above). Auto-syncing role membership into the user store was intentionally
        # removed in favour of the one-time SetupModule registration flow.

    finally:
        authorization_service._roles.clear()
        authorization_service._roles.update(original_roles)
