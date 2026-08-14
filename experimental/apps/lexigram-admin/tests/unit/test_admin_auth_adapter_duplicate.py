from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from lexigram.admin.auth.adapter import AdminAuthAdapter
from lexigram.contracts.auth import AuthProviderProtocol
from lexigram.di import Container


@pytest.mark.asyncio
async def test_register_handles_duplicate_create_by_updating_existing():
    # Setup a user config entry
    user = SimpleNamespace(
        user_id="admin",
        username="admin",
        email="admin@example.com",
        hashed_password="$2b$12$dummyhash",
        roles=["admin"],
        permissions=[],
    )

    # Create a config object with users and roles (not AdminAuthConfig)
    auth_config = SimpleNamespace(
        users=[user],
        roles={},
        session_secret="test-secret",  # Required for AdminAuthConfig compatibility
    )

    # Fake store that raises on create (duplicate) but returns an existing user
    was_updated = {"updated": False}

    class FakeStore:
        async def create_user(self, *args, **kwargs):
            raise Exception(
                'duplicate key value violates unique constraint "users_email_key"\nDETAIL:  Key (email)=(admin@example.com) already exists.',
            )

        async def get_user_by_username(self, username):
            return SimpleNamespace(
                username=username, email="admin@example.com", roles=[], permissions=[],
            )

        async def get_user_by_email(self, email):
            return SimpleNamespace(
                username="admin", email=email, roles=[], permissions=[],
            )

        async def update_user(self, user):
            was_updated["updated"] = True
            return user

    fake_store = FakeStore()

    # Register a fake AuthProvider-like object carrying user_store
    from lexigram.auth.di import AuthenticationProvider

    container = Container()

    class FakeProvider:
        name = "fake"
        priority = 1
        critical = False
        dependencies = []
        def __init__(self, store):
            self.user_store = store
            
        def register(self, container):
            pass
            
        async def boot(self):
            pass
            
        async def shutdown(self):
            pass

        async def health_check(self):
            from lexigram.contracts.core import HealthStatus
            return HealthStatus.HEALTHY

    auth_provider = FakeProvider(fake_store)
    container.singleton(AuthenticationProvider, lambda: auth_provider)
    container.singleton(AuthProviderProtocol, lambda: auth_provider)

    adapter = AdminAuthAdapter(auth_config=auth_config, authorization_service=MagicMock())

    # Auto-seeding of users from config was intentionally removed in favour of
    # the one-time super-admin registration flow (SetupModule).  register()
    # should complete successfully with roles={} (nothing to sync).
    await adapter.sync(container)

    # No user creation/update should have happened since seeding was removed.
    assert was_updated["updated"] is False


@pytest.mark.asyncio
async def test_create_user_handles_duplicate_by_returning_existing():
    # Setup the container and a fake provider that raises on create
    existing_user = SimpleNamespace(
        user_id="u1",
        username="admin",
        email="admin@example.com",
        roles=["admin"],
        permissions=[],
    )

    class FakeAuthProvider:
        name = "fake"
        priority = 1
        critical = False
        dependencies = []

        def __init__(self):
            self.user_store = SimpleNamespace()
            
        def register(self, container):
            pass

        async def boot(self):
            pass

        async def shutdown(self):
            pass

        async def health_check(self):
            from lexigram.contracts.core import HealthStatus
            return HealthStatus.HEALTHY

        async def create_user(self, username, email, password=None):
            raise Exception(
                'duplicate key value violates unique constraint "users_email_key"\nDETAIL:  Key (email)=(admin@example.com) already exists.',
            )

    async def get_by_email(email):
        return existing_user

    async def get_by_username(username):
        return existing_user

    async def update_user(u):
        existing_user.roles = u.roles
        return existing_user

    auth_provider = FakeAuthProvider()
    # create_user belongs on the store, not the provider (A1.3)
    async def _store_create(name, email, hashed_password=None, roles=None, permissions=None, **kwargs):
        raise Exception(
            'duplicate key value violates unique constraint "users_email_key"\nDETAIL:  Key (email)=(admin@example.com) already exists.',
        )

    auth_provider.user_store.create_user = _store_create
    auth_provider.user_store.get_user_by_email = get_by_email
    auth_provider.user_store.get_user_by_username = get_by_username
    auth_provider.user_store.update_user = update_user

    container = Container()
    from lexigram.auth.authn.security import PasswordHasher
    from lexigram.auth.di import AuthenticationProvider
    from lexigram.contracts.auth import PasswordHasherProtocol

    container.singleton(AuthenticationProvider, lambda: auth_provider)
    container.singleton(AuthProviderProtocol, lambda: auth_provider)
    # PasswordHasherProtocol must be registered — no AdminBcryptHasher fallback.
    container.singleton(PasswordHasherProtocol, PasswordHasher)

    # Create a config object with session_secret (required for compatibility)
    auth_config = SimpleNamespace(session_secret="test-secret")
    adapter = AdminAuthAdapter(auth_config, MagicMock())

    # Should not raise and should return the existing user
    user = await adapter.create_user(
        container, username="admin", email="admin@example.com", password="x",
    )
    assert user is existing_user
