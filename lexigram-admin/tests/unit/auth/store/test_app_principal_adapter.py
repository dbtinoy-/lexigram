"""AppPrincipalUserStoreAdapter maps AdminUserStoreProtocol over the provider."""

from __future__ import annotations

import pytest

from lexigram.admin.auth.store.app_principal import AppPrincipalUserStoreAdapter
from lexigram.contracts.admin import AdminPrincipal


class FakeProvider:
    def __init__(self) -> None:
        self.principals = {
            "u1": AdminPrincipal(
                user_id="u1", name="Ada", email="ada@example.com", roles=["superadmin"]
            )
        }
        self.synced: list[tuple[str, list[str]]] = []

    async def principal_for(self, user_id: str) -> AdminPrincipal | None:
        return self.principals.get(user_id)

    async def list_principals(self) -> list[AdminPrincipal]:
        return list(self.principals.values())

    async def create_principal(self, name, email, password, roles=None) -> AdminPrincipal:  # noqa: ANN001
        p = AdminPrincipal(user_id="u9", name=name, email=email, roles=roles or [])
        self.principals["u9"] = p
        return p

    async def update_principal(self, principal: AdminPrincipal) -> None:
        self.principals[principal.user_id] = principal

    async def delete_principal(self, user_id: str) -> None:
        self.principals.pop(user_id, None)

    async def authenticate(self, email: str, password: str) -> AdminPrincipal | None:
        del password
        for p in self.principals.values():
            if p.email == email:
                return p
        return None

    async def sync_roles(self, user_id: str, roles: list[str]) -> None:
        self.synced.append((user_id, roles))

    async def ensure_schema(self) -> None:
        return None


@pytest.mark.asyncio
async def test_adapter_get_user_by_email() -> None:
    store = AppPrincipalUserStoreAdapter(provider=FakeProvider())
    user = await store.get_user_by_email("ada@example.com")
    assert user is not None
    assert getattr(user, "user_id") == "u1"


@pytest.mark.asyncio
async def test_adapter_create_upserts_via_provider() -> None:
    store = AppPrincipalUserStoreAdapter(provider=FakeProvider())
    await store.create_user(name="New", email="n@example.com", hashed_password="h")
    assert await store.get_admin_count() == 2


@pytest.mark.asyncio
async def test_adapter_sync_roles_delegates() -> None:
    provider = FakeProvider()
    store = AppPrincipalUserStoreAdapter(provider=provider)
    await store.update_user(
        type("U", (), {"user_id": "u1", "name": "Ada", "email": "ada@example.com",
                        "roles": ["viewer"], "permissions": [], "hashed_password": "h",
                        "is_active": True})()
    )
    assert provider.synced == [("u1", ["viewer"])]


@pytest.mark.asyncio
async def test_adapter_update_user_forwards_hashed_password() -> None:
    provider = FakeProvider()
    store = AppPrincipalUserStoreAdapter(provider=provider)
    await store.update_user(
        type("U", (), {"user_id": "u1", "name": "Ada", "email": "ada@example.com",
                        "roles": ["superadmin"], "permissions": [],
                        "hashed_password": "pbkdf2$newhash", "is_active": True})()
    )
    assert provider.principals["u1"].hashed_password == "pbkdf2$newhash"


@pytest.mark.asyncio
async def test_adapter_update_user_empty_hash_not_forwarded() -> None:
    provider = FakeProvider()
    store = AppPrincipalUserStoreAdapter(provider=provider)
    await store.update_user(
        type("U", (), {"user_id": "u1", "name": "Ada", "email": "ada@example.com",
                        "roles": ["superadmin"], "permissions": [],
                        "hashed_password": "", "is_active": True})()
    )
    assert provider.principals["u1"].hashed_password == ""
