"""Tests for the batch_load() dict→ordered-list adapter.

Verifies that batch_load() correctly wraps loader functions that return
either dicts or lists, converting them into properly ordered list results
matching the input key order.
"""

from __future__ import annotations

import pytest

from lexigram.graphql.dataloader.batch import batch_load


class TestBatchLoadDictAdapter:
    """Tests for batch_load() dict→ordered-list conversion."""

    @pytest.mark.asyncio
    async def test_dict_result_maps_to_ordered_list(self) -> None:
        """batch_load() with dict-returning fn maps keys to ordered list."""
        data = {"a": "apple", "b": "banana", "c": "cherry"}

        async def load_by_key(keys: list[str]) -> dict[str, str]:
            return {k: data[k] for k in keys if k in data}

        wrapped = batch_load(load_by_key)
        result = await wrapped(["c", "a", "b"])
        assert result == ["cherry", "apple", "banana"]

    @pytest.mark.asyncio
    async def test_dict_result_missing_keys_return_none(self) -> None:
        """batch_load() returns None for keys missing from dict result."""
        async def load_by_key(keys: list[str]) -> dict[str, str]:
            return {"x": "found"}

        wrapped = batch_load(load_by_key)
        result = await wrapped(["x", "y", "z"])
        assert result == ["found", None, None]

    @pytest.mark.asyncio
    async def test_dict_result_preserves_input_order(self) -> None:
        """batch_load() preserves input key order even when dict is unordered."""
        async def load_users(ids: list[int]) -> dict[int, str]:
            return {3: "Charlie", 1: "Alice", 2: "Bob"}

        wrapped = batch_load(load_users)
        result = await wrapped([1, 2, 3])
        assert result == ["Alice", "Bob", "Charlie"]

    @pytest.mark.asyncio
    async def test_list_result_with_key_fn(self) -> None:
        """batch_load() with list-returning fn and key_fn maps to ordered list."""
        class User:
            def __init__(self, id: int, name: str) -> None:
                self.id = id
                self.name = name

        async def load_users(ids: list[int]) -> list[User]:
            users = {1: User(1, "Alice"), 2: User(2, "Bob"), 3: User(3, "Carol")}
            return [users[i] for i in ids if i in users]

        wrapped = batch_load(load_users, key_fn=lambda u: u.id)
        result = await wrapped([3, 1, 2])
        assert [r.name for r in result if r] == ["Carol", "Alice", "Bob"]  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_list_result_missing_keys_return_none(self) -> None:
        """batch_load() with key_fn returns None for keys not in list result."""
        class Item:
            def __init__(self, id: int) -> None:
                self.id = id

        async def load_items(ids: list[int]) -> list[Item]:
            return [Item(1)]  # only item 1 found

        wrapped = batch_load(load_items, key_fn=lambda i: i.id)
        result = await wrapped([1, 99, 2])
        assert result[0] is not None
        assert result[0].id == 1  # type: ignore[union-attr]
        assert result[1] is None
        assert result[2] is None

    @pytest.mark.asyncio
    async def test_list_result_same_order_no_key_fn(self) -> None:
        """batch_load() with list of same length as keys assumes same order."""
        async def load_values(keys: list[str]) -> list[int]:
            return [len(k) for k in keys]

        wrapped = batch_load(load_values)
        result = await wrapped(["hi", "hello", "hey"])
        assert result == [2, 5, 3]

    @pytest.mark.asyncio
    async def test_empty_keys_returns_empty_list(self) -> None:
        """batch_load() with empty key list returns empty result."""
        async def load_dict(keys: list[str]) -> dict[str, str]:
            return {}

        wrapped = batch_load(load_dict)
        result = await wrapped([])
        assert result == []

    @pytest.mark.asyncio
    async def test_dict_result_with_empty_dict(self) -> None:
        """batch_load() with empty dict result returns all Nones."""
        async def load_nothing(keys: list[str]) -> dict[str, str]:
            return {}

        wrapped = batch_load(load_nothing)
        result = await wrapped(["a", "b"])
        assert result == [None, None]
