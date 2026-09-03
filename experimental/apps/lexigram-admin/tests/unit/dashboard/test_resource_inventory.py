"""Tests for the mount-time resource inventory read-model."""

from __future__ import annotations

from typing import Any

from lexigram.admin.dashboard.resource_inventory import (
    DEFAULT_SNAPSHOT_LIMIT,
    ResourceCount,
    ResourceInventory,
)


class _CountingSource:
    def __init__(self, total: int) -> None:
        self.total = total
        self.count_calls = 0

    async def count(self, query: Any) -> int:
        self.count_calls += 1
        return self.total


class _FindManyOnlySource:
    """Data source without ``count`` — inventory must fall back to total."""

    def __init__(self, total: int) -> None:
        self._total = total

    async def find_many(self, query: Any) -> Any:
        class _Result:
            items = ()
            total = self._total

        return _Result()


class _RaisingSource:
    async def count(self, query: Any) -> int:
        raise RuntimeError("db down")


class _Meta:
    def __init__(self, label_plural: str | None) -> None:
        self.label_plural = label_plural


class _Resource:
    def __init__(
        self,
        *,
        data_source: Any | None = None,
        label: str | None = None,
        label_plural: str | None = None,
        icon: str | None = None,
    ) -> None:
        self._data_source = data_source
        self.label = label
        self.meta = _Meta(label_plural)
        if icon is not None:
            self.icon = icon


async def test_snapshot_counts_via_count_method() -> None:
    source = _CountingSource(42)
    inventory = ResourceInventory({"products": _Resource(data_source=source)})
    (item,) = await inventory.snapshot()
    assert item == ResourceCount(name="products", label="Products", icon="box", count=42)
    assert source.count_calls == 1


async def test_snapshot_falls_back_to_find_many_total() -> None:
    inventory = ResourceInventory(
        {"orders": _Resource(data_source=_FindManyOnlySource(7))}
    )
    (item,) = await inventory.snapshot()
    assert item.count == 7


async def test_snapshot_prefers_meta_label_plural_then_label() -> None:
    inventory = ResourceInventory(
        {
            "a": _Resource(data_source=_CountingSource(1), label_plural="Fancy Items"),
            "b": _Resource(data_source=_CountingSource(2), label="Plain Label"),
            "some_thing": _Resource(data_source=_CountingSource(3)),
        }
    )
    labels = [item.label for item in await inventory.snapshot()]
    assert labels == ["Fancy Items", "Plain Label", "Some Thing"]


async def test_snapshot_uses_resource_icon_with_box_default() -> None:
    inventory = ResourceInventory(
        {
            "a": _Resource(data_source=_CountingSource(1), icon="package"),
            "b": _Resource(data_source=_CountingSource(2)),
        }
    )
    icons = [item.icon for item in await inventory.snapshot()]
    assert icons == ["package", "box"]


async def test_snapshot_is_fail_soft_per_resource() -> None:
    inventory = ResourceInventory(
        {
            "bad": _Resource(data_source=_RaisingSource()),
            "good": _Resource(data_source=_CountingSource(5)),
        }
    )
    items = await inventory.snapshot()
    assert [item.count for item in items] == [None, 5]


async def test_snapshot_includes_resources_without_data_source() -> None:
    inventory = ResourceInventory({"bare": _Resource()})
    (item,) = await inventory.snapshot()
    assert item.count is None


async def test_snapshot_respects_limit_and_mount_order() -> None:
    resources = {
        f"r{i:02d}": _Resource(data_source=_CountingSource(i))
        for i in range(DEFAULT_SNAPSHOT_LIMIT + 4)
    }
    inventory = ResourceInventory(resources)
    items = await inventory.snapshot()
    assert len(items) == DEFAULT_SNAPSHOT_LIMIT
    assert [item.name for item in items] == list(resources)[:DEFAULT_SNAPSHOT_LIMIT]
    two = await inventory.snapshot(limit=2)
    assert [item.name for item in two] == ["r00", "r01"]


async def test_snapshot_sees_resources_added_after_construction() -> None:
    live: dict[str, Any] = {}
    inventory = ResourceInventory(live)
    assert inventory.is_empty()
    live["late"] = _Resource(data_source=_CountingSource(9))
    assert not inventory.is_empty()
    (item,) = await inventory.snapshot()
    assert item.count == 9


async def test_snapshot_empty_inventory_returns_no_items() -> None:
    inventory = ResourceInventory({})
    assert await inventory.snapshot() == ()


async def test_snapshot_negative_limit_returns_no_items() -> None:
    inventory = ResourceInventory(
        {"a": _Resource(data_source=_CountingSource(1))}
    )
    assert await inventory.snapshot(limit=-1) == ()


__all__ = [
    "test_snapshot_counts_via_count_method",
    "test_snapshot_empty_inventory_returns_no_items",
    "test_snapshot_falls_back_to_find_many_total",
    "test_snapshot_includes_resources_without_data_source",
    "test_snapshot_is_fail_soft_per_resource",
    "test_snapshot_negative_limit_returns_no_items",
    "test_snapshot_prefers_meta_label_plural_then_label",
    "test_snapshot_respects_limit_and_mount_order",
    "test_snapshot_sees_resources_added_after_construction",
    "test_snapshot_uses_resource_icon_with_box_default",
]
