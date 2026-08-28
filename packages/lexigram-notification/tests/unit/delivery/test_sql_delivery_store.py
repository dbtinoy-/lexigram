"""Regression tests for the SQL delivery-state store.

``SqlDeliveryStore.create_pending`` previously crashed because the
``message`` payload (a dict) was passed raw to the driver; the CRUD
layer now JSON-encodes dict/list values before binding.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lexigram.notification.delivery.stores import SqlDeliveryStore
from lexigram.sql.providers.sqlite_provider import SQLiteProvider


@pytest.fixture
async def store():
    """SqlDeliveryStore over an in-memory SQLite provider."""
    provider = SQLiteProvider(database_path=":memory:")
    await provider.connect()
    try:
        yield SqlDeliveryStore(provider)
    finally:
        await provider.connection_manager.disconnect()


@pytest.mark.asyncio
async def test_create_pending_persists_message_payload(store) -> None:
    """A dict message payload is JSON-encoded and readable back."""
    msg = SimpleNamespace(to=["a@example.com"], subject="Hello", body="World")
    delivery_id = await store.create_pending(msg)
    assert delivery_id

    rows = await store.due_deliveries()
    assert len(rows) == 1
    state = rows[0]
    assert state["delivery_id"] == delivery_id
    assert state["recipient"] == "a@example.com"
    # message column round-trips as parsed JSON (due_deliveries loads it)
    assert state["message"] == {"subject": "Hello", "body": "World"}


@pytest.mark.asyncio
async def test_mark_delivered_updates_row(store) -> None:
    """mark_delivered applies against the stored row."""
    msg = SimpleNamespace(to=["b@example.com"], subject="S", body="B")
    delivery_id = await store.create_pending(msg)
    await store.mark_delivered(delivery_id)
    result = await store._db.execute_query(  # noqa: SLF001 — test-only
        "SELECT status FROM notification_delivery_state WHERE delivery_id = ?",
        [delivery_id],
    )
    assert result.rows[0]["status"] == "delivered"
