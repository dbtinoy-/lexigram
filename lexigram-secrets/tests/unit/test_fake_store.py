from __future__ import annotations

import pytest

from lexigram.testing.fakes import FakeRotatableSecretStore


class TestFakeRotatableSecretStore:
    @pytest.fixture
    def store(self) -> FakeRotatableSecretStore:
        return FakeRotatableSecretStore()

    async def test_get_returns_none_for_missing(self, store: FakeRotatableSecretStore) -> None:
        result = await store.get("nonexistent")
        assert result is None

    async def test_set_and_get(self, store: FakeRotatableSecretStore) -> None:
        await store.set("key", "value")
        result = await store.get("key")
        assert result == "value"

    async def test_get_bulk(self, store: FakeRotatableSecretStore) -> None:
        await store.set("a", "1")
        await store.set("b", "2")
        result = await store.get_bulk("a", "b", "c")
        assert result == {"a": "1", "b": "2"}

    async def test_delete_removes_key(self, store: FakeRotatableSecretStore) -> None:
        await store.set("key", "val")
        await store.delete("key")
        assert await store.get("key") is None

    async def test_delete_nonexistent_is_noop(self, store: FakeRotatableSecretStore) -> None:
        await store.delete("nobody")

    async def test_rotate_generates_new_value(self, store: FakeRotatableSecretStore) -> None:
        await store.set("key", "original")
        rotated = await store.rotate("key")
        assert rotated.key == "key"
        assert str(rotated.value) != "original"
        assert rotated.version >= 1

    async def test_rotate_increments_version(self, store: FakeRotatableSecretStore) -> None:
        await store.set("key", "v0")
        v1 = await store.rotate("key")
        v2 = await store.rotate("key")
        assert v2.version == v1.version + 1

    async def test_get_current_version(self, store: FakeRotatableSecretStore) -> None:
        await store.set("key", "latest")
        current = await store.get_current_version("key")
        assert str(current.value) == "latest"
        assert current.version == 1

    async def test_get_current_version_missing_raises(self, store: FakeRotatableSecretStore) -> None:
        with pytest.raises(KeyError):
            await store.get_current_version("nonexistent")

    async def test_get_version_returns_specific(self, store: FakeRotatableSecretStore) -> None:
        await store.set("key", "v1")
        await store.set("key", "v2")
        v1 = await store.get_version("key", 1)
        assert v1 == "v1"
        v2 = await store.get_version("key", 2)
        assert v2 == "v2"

    async def test_get_version_missing_is_none(self, store: FakeRotatableSecretStore) -> None:
        result = await store.get_version("key", 99)
        assert result is None

    async def test_list_versions_order(self, store: FakeRotatableSecretStore) -> None:
        await store.set("key", "a")
        await store.rotate("key")
        await store.rotate("key")
        versions = await store.list_versions("key")
        assert len(versions) >= 2
        assert versions[0].version > versions[1].version

    async def test_list_versions_empty(self, store: FakeRotatableSecretStore) -> None:
        versions = await store.list_versions("nonexistent")
        assert versions == []

    async def test_secret_value_masked_repr(self, store: FakeRotatableSecretStore) -> None:
        await store.set("key", "secret123")
        rotated = await store.rotate("key")
        assert "secret123" not in repr(rotated.value)
        assert "***masked***" in repr(rotated.value)
