import asyncio
import os

import pytest
import pytest_asyncio

from lexigram.tasks.backends.postgres import PostgresTaskConfig, PostgresTaskQueue

TEST_DSN = os.environ.get("TEST_POSTGRES_DSN")


@pytest_asyncio.fixture
async def pg_queue() -> PostgresTaskQueue:
    if not TEST_DSN:
        pytest.skip("TEST_POSTGRES_DSN not set; skipping Postgres integration tests")

    cfg = PostgresTaskConfig(dsn=TEST_DSN, pool_min_size=1, pool_max_size=2)
    q = PostgresTaskQueue(cfg)
    await q.connect()

    # clean table if present
    async with q._pool.acquire() as conn:
        await conn.execute(f"TRUNCATE TABLE {cfg.table}")

    try:
        yield q

    finally:
        async with q._pool.acquire() as conn:
            await conn.execute(f"TRUNCATE TABLE {cfg.table}")
        await q.close()


@pytest.mark.asyncio
async def test_enqueue_dequeue_ack_roundtrip(pg_queue: PostgresTaskQueue) -> None:
    payload = {"task": "send_email", "to": "a@example.com"}

    job_id = await pg_queue.enqueue(payload, priority=5)
    assert job_id

    item = await pg_queue.dequeue()
    assert item is not None
    assert item["id"] == job_id
    assert item["payload"]["task"] == "send_email"

    # Acknowledge and ensure no pending tasks remain
    await pg_queue.ack(job_id)
    count = await pg_queue.get_task_count()
    assert count == 0


@pytest.mark.asyncio
async def test_visibility_timeout_requeues_task(pg_queue: PostgresTaskQueue) -> None:
    job_id = await pg_queue.enqueue({"task": "retry_me"})

    item = await pg_queue.dequeue()
    assert item and item["id"] == job_id

    # Wait for visibility to expire and call requeue
    await asyncio.sleep(1.1)
    affected = await pg_queue.requeue_stalled(1)
    assert affected >= 1

    # Now another worker should be able to dequeue the same job
    item2 = await pg_queue.dequeue()
    assert item2 and item2["id"] == job_id

    await pg_queue.ack(job_id)


@pytest.mark.asyncio
async def test_nack_with_delay_respects_available_at(
    pg_queue: PostgresTaskQueue,
) -> None:
    job_id = await pg_queue.enqueue({"task": "delay_me"})
    item = await pg_queue.dequeue()
    assert item and item["id"] == job_id

    # Nack with 2s delay
    await pg_queue.nack(job_id, delay_seconds=2)

    # Immediately no task should be available
    none_item = await pg_queue.dequeue()
    assert none_item is None

    # After delay, it should be available again
    await asyncio.sleep(2.1)
    item2 = await pg_queue.dequeue()
    assert item2 and item2["id"] == job_id
    await pg_queue.ack(job_id)


@pytest.mark.asyncio
async def test_max_attempts_moves_task_to_failed(pg_queue: PostgresTaskQueue) -> None:
    # Create a queue with max_attempts = 1 for this test
    cfg = PostgresTaskConfig(
        dsn=pg_queue.config.dsn, pool_min_size=1, pool_max_size=2, max_attempts=1,
    )
    q2 = PostgresTaskQueue(cfg)
    await q2.connect()

    # Clean table and use new queue instance
    async with q2._pool.acquire() as conn:
        await conn.execute(f"TRUNCATE TABLE {cfg.table}")

    jid = await q2.enqueue({"task": "will_fail"})

    item1 = await q2.dequeue()
    assert item1 and item1["id"] == jid

    # Requeue immediately (visibility 0) -> it will be requeued first (attempts == 1)
    await q2.requeue_stalled(0)

    # Dequeue again: attempts == 2 now, which exceeds max_attempts=1
    item2 = await q2.dequeue()
    assert item2 and item2["id"] == jid

    # Now requeue_stalled should mark it failed
    affected = await q2.requeue_stalled(0)
    assert affected >= 1

    status = await q2.get_task_status(jid)
    assert status == "failed"

    await q2.clear()
    await q2.close()


@pytest.mark.asyncio
async def test_concurrent_dequeue_returns_unique_tasks(
    pg_queue: PostgresTaskQueue,
) -> None:
    # Enqueue multiple tasks
    ids = []
    for i in range(5):
        jid = await pg_queue.enqueue({"n": i})
        ids.append(jid)

    async def worker():
        item = await pg_queue.dequeue()
        if not item:
            return None
        await pg_queue.ack(item["id"])
        return item["id"]

    results = await pytest.asyncio.gather(*(worker() for _ in range(5)))
    # Filter out None and ensure uniqueness
    got = list(filter(lambda r: r, results))
    assert len(got) == 5
    assert len(set(got)) == 5
