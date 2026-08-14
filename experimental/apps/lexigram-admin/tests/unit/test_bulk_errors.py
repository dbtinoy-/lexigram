import pytest

from lexigram.admin.actions.bulk_manager import BulkActionManager


class BadDataSource:
    async def create_snapshot(self, ids):
        return "snap"

    async def bulk_update(self, ids, updates):
        raise RuntimeError("boom")

    async def fetch_by_ids(self, ids):
        return []

    async def restore_snapshot(self, snapshot_id):
        return 0


@pytest.mark.asyncio
async def test_bulk_edit_unexpected_error_propagates(caplog):
    """Infrastructure exceptions from the data source propagate; they are never
    swallowed into a result wrapper."""
    ds = BadDataSource()
    manager = BulkActionManager(data_source=ds)

    caplog.set_level("ERROR", logger="lexigram")
    with pytest.raises(RuntimeError, match="boom"):
        await manager.bulk_edit(
            ids=[1, 2, 3], updates={"a": 1}, create_snapshot=True,
        )
