import pytest

from lexigram.admin.auth.store import AuthProviderAdminUserStore
from lexigram.auth.authn.security import PasswordHasher
from lexigram.auth.di import AuthenticationProvider


@pytest.mark.asyncio
async def test_auth_provider_admin_user_store_delegates():
    from lexigram.auth.config import AuthConfig, JWTConfig
    _key = "test-user-store-adapter-key-32byte"
    auth = AuthenticationProvider(config=AuthConfig(secret_key=_key, token=JWTConfig(secret_key=_key)))
    # create a user directly in the store (providers don't own user creation)
    hashed_pw = await PasswordHasher().hash("Secret1!")
    created = await auth.user_store.create_user(
        name="u1", email="u1@example.com", hashed_password=hashed_pw,
    )
    store = AuthProviderAdminUserStore(auth)

    # Sanity-check underlying auth provider user store
    u_direct = await auth.user_store.get_user_by_username("u1")
    assert u_direct is not None, "auth.user_store.get_user_by_username returned None"

    got = await store.get_by_username("u1")
    assert got is not None
    assert got.name == "u1"

    got2 = await store.get_by_email("u1@example.com")
    assert got2 is not None

    got_id = await store.get_by_id(created.user_id)
    assert got_id is not None

    # authenticate via auth_provider
    authed = await store.authenticate("u1@example.com", "Secret1!")
    assert authed is not None

    c = await store.count()
    assert c >= 1
