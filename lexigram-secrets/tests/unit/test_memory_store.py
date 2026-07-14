"""InMemoryRotatableSecretStore full API coverage."""

from __future__ import annotations

import pytest

from lexigram.secrets.backends.memory import InMemoryRotatableSecretStore


@pytest.mark.asyncio
async def test_memory_store_get_set_delete() -> None:
    store = InMemoryRotatableSecretStore()
    assert await store.get("missing") is None
    await store.set("api_key", "v1")
    assert await store.get("api_key") == "v1"
    await store.set("api_key", "v2")
    assert await store.get("api_key") == "v2"
    await store.delete("api_key")
    assert await store.get("api_key") is None
    await store.delete("never-existed")


@pytest.mark.asyncio
async def test_memory_store_get_bulk() -> None:
    store = InMemoryRotatableSecretStore()
    await store.set("a", "1")
    assert await store.get_bulk("a", "b") == {"a": "1"}


@pytest.mark.asyncio
async def test_memory_store_rotate() -> None:
    store = InMemoryRotatableSecretStore()
    rotated = await store.rotate("token")
    assert rotated.key == "token"
    assert rotated.version == 1
    assert str(rotated.value) == await store.get("token")
    assert rotated.created_at is not None


@pytest.mark.asyncio
async def test_memory_store_version_history() -> None:
    store = InMemoryRotatableSecretStore()
    await store.set("k", "first")
    await store.set("k", "second")
    assert await store.get_version("k", 1) == "first"
    assert await store.get_version("k", 2) == "second"
    assert await store.get_version("k", 99) is None
    assert await store.get_version("absent", 1) is None
    versions = await store.list_versions("k")
    assert [v.version for v in versions] == [2, 1]
    assert await store.list_versions("absent") == []
    current = await store.get_current_version("k")
    assert current.version == 2
    assert str(current.value) == "second"
    with pytest.raises(KeyError):
        await store.get_current_version("absent")