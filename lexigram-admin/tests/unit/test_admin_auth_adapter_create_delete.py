from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from lexigram.admin.auth.adapter import AdminAuthAdapter
from lexigram.auth.authn.security import PasswordHasher
from lexigram.auth.di import AuthenticationProvider
from lexigram.contracts.auth import AuthProviderProtocol, PasswordHasherProtocol
from lexigram.di import Container


@pytest.mark.asyncio
async def test_create_user_via_adapter_creates_user():
    container = Container()
    # Use real in-memory AuthProvider to exercise create_user
    from lexigram.auth.config import AuthConfig, JWTConfig
    _key = "test-secret-key-for-admin-tests-32b"
    auth_provider = AuthenticationProvider(config=AuthConfig(secret_key=_key, token=JWTConfig(secret_key=_key)))
    container.singleton(AuthenticationProvider, lambda: auth_provider)
    container.singleton(AuthProviderProtocol, lambda: auth_provider)
    # PasswordHasherProtocol must be registered — previously AdminBcryptHasher
    # was used as a fallback; now the container is the single source of truth.
    container.singleton(PasswordHasherProtocol, PasswordHasher)

    adapter = AdminAuthAdapter(SimpleNamespace(), MagicMock())
    user = await adapter.create_user(
        container, username="bob", email="bob@example.com", password="Secret1!",
    )

    # AuthenticationProvider.create_user returns a User-like object
    assert user is not None
    stored = await auth_provider.user_store.get_user_by_username("bob")
    assert stored is not None
    assert stored.name == "bob"


@pytest.mark.asyncio
async def test_delete_user_via_adapter_deletes_user():
    container = Container()
    from lexigram.auth.config import AuthConfig, JWTConfig
    _key = "test-secret-key-for-admin-tests-32b"
    auth_provider = AuthenticationProvider(config=AuthConfig(secret_key=_key, token=JWTConfig(secret_key=_key)))
    container.singleton(AuthenticationProvider, lambda: auth_provider)
    container.singleton(AuthProviderProtocol, lambda: auth_provider)

    # Create a user to delete
    hashed_pw = await __import__("lexigram.auth.authn.security", fromlist=["PasswordHasher"]).PasswordHasher.hash("Secure2#")
    created = await auth_provider.user_store.create_user(
        name="charlie", email="charlie@example.com", hashed_password=hashed_pw,
    )
    user_id = created.user_id

    adapter = AdminAuthAdapter(SimpleNamespace(), MagicMock())
    await adapter.delete_user(container, user_id)

    # Ensure user no longer exists
    stored = await auth_provider.user_store.get_user_by_username("charlie")
    assert stored is None
