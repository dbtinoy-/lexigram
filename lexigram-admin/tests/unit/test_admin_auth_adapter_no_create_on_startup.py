from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from lexigram.admin.auth.adapter import AdminAuthAdapter
from lexigram.admin.auth import AdminAuthConfig
from lexigram.di import Container


@pytest.mark.asyncio
async def test_register_skips_creating_users_when_disabled():
    # user config with missing user
    user = SimpleNamespace(
        username="missing",
        email="missing@example.com",
        hashed_password="$2b$hash",
        roles=["admin"],
        permissions=[],
    )
    auth_config = AdminAuthConfig(enabled=False, users=[user], roles={})

    class FakeStore:
        def __init__(self):
            self.created = False

        async def get_user_by_username(self, username):
            return None

        async def get_user_by_email(self, email):
            return None

        async def create_user(self, *args, **kwargs):
            self.created = True
            return SimpleNamespace(
                user_id="uX", username=kwargs.get("username"), email=kwargs.get("email"),
            )

    fake_store = FakeStore()
    container = Container()
    from lexigram.contracts.auth import AuthProviderProtocol
    # Provide a fake AuthProvider-like object with a user_store attr
    auth_provider = SimpleNamespace(user_store=fake_store, session_manager=None)
    container.singleton(AuthProviderProtocol, lambda: auth_provider)

    adapter = AdminAuthAdapter(auth_config, MagicMock())

    # Should not raise and should not create user
    await adapter.sync(container)

    assert fake_store.created is False
