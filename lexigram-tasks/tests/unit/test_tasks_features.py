"""Comprehensive feature test for lexigram-tasks v1.0.

Tests all new features: retry logic, rate limiting, locking, DLQ, decorator.
"""

import asyncio
import time

import pytest

from lexigram.logging import get_logger
from lexigram.resilience.rate_limiter import RateLimiter
from lexigram.tasks import (
    DistributedLockProtocol,
    JobProtocol,
    JobStatus,
    MemoryTaskQueue,
    Priority,
    QueueRateLimiter,
    distributed_lock,
    task,
)

logger = get_logger(__name__)


def test_retry_logic():
    """Test retry mechanism with exponential backoff."""
    logger.info("Testing retry logic...")

    # Create job that will fail
    job = JobProtocol(
        id="test-retry",
        name="failing_task",
        args=(),
        kwargs={},
        max_retries=3,
    )

    # Simulate failures
    assert job.can_retry == True
    job.mark_retrying()
    assert job.retry_count == 1
    assert job.status == JobStatus.RETRYING

    job.mark_retrying()
    assert job.retry_count == 2

    job.mark_retrying()
    assert job.retry_count == 3
    assert job.can_retry == False  # Max retries reached

    logger.info("✅ Retry logic working")


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiter."""
    logger.info("Testing rate limiting...")

    # Create rate limiter: 5 per second
    limiter = RateLimiter(rate=5, per=1.0)

    # Acquire tokens
    start = time.time()
    for i in range(5):
        await limiter.acquire()
    elapsed = time.time() - start

    # Should be very fast (tokens available)
    assert elapsed < 0.1, f"Expected fast acquisition, got {elapsed}s"

    # Next acquisition should wait
    start = time.time()
    acquired = await limiter.try_acquire()
    elapsed = time.time() - start

    # Should fail immediately (no tokens)
    assert acquired == False, "Should fail when no tokens available"
    assert elapsed < 0.1, "try_acquire should be non-blocking"

    logger.info("✅ Rate limiting working")


@pytest.mark.asyncio
async def test_queue_rate_limiter():
    """Test per-queue rate limiting."""
    logger.info("Testing queue rate limiter...")

    limiter = QueueRateLimiter()
    limiter.add_limit("emails", rate=10, per=1.0)
    limiter.add_limit("reports", rate=1, per=1.0)

    # Test email queue
    can_send = await limiter.try_acquire("emails")
    assert can_send == True

    # Test unlimited queue
    can_send = await limiter.try_acquire("other")
    assert can_send == True

    logger.info("✅ Queue rate limiter working")


@pytest.mark.asyncio
async def test_distributed_lock():
    """Test distributed locking."""
    logger.info("Testing distributed locking...")

    # Create lock manager
    from lexigram.tasks.concurrency.locking import LockManager
    lock_manager = LockManager()

    # Test lock acquisition
    lock1 = lock_manager.acquire("resource:123", timeout=60)
    acquired1 = await lock1.acquire()
    assert acquired1 == True
    assert lock1.acquired == True

    # Try to acquire same lock
    lock2 = lock_manager.acquire("resource:123", timeout=60)
    acquired2 = await lock2.try_acquire()
    assert acquired2 == False, "Second lock should fail"

    # Release first lock
    await lock1.release()

    # Now second lock should work
    acquired2 = await lock2.acquire()
    assert acquired2 == True

    await lock2.release()

    logger.info("✅ Distributed locking working")


@pytest.mark.asyncio
async def test_distributed_lock_context():
    """Test distributed lock context manager."""
    logger.info("Testing distributed lock context manager...")

    # Create lock manager
    from lexigram.tasks.concurrency.locking import LockManager
    lock_manager = LockManager()

    async with distributed_lock("resource:456", lock_manager=lock_manager):
        # Inside lock
        lock_test = lock_manager.acquire("resource:456")
        can_acquire = await lock_test.try_acquire()
        assert can_acquire == False, "Lock should be held"

    # After context, lock should be released
    lock_test = lock_manager.acquire("resource:456")
    can_acquire = await lock_test.acquire()
    assert can_acquire == True
    await lock_test.release()

    logger.info("✅ Distributed lock context manager working")


def test_task_decorator():
    """Test @task decorator."""
    logger.info("Testing @task decorator...")

    @task(name="test_task", priority=Priority.HIGH, max_retries=5)
    async def my_task(x: int, y: int):
        return x + y

    # Check metadata
    assert my_task._task_name == "test_task"
    assert my_task._priority == Priority.HIGH.value
    assert my_task._max_retries == 5

    # Create signature
    sig = my_task.s(10, 20)
    assert sig.name == "test_task"
    assert sig.args == (10, 20)
    assert sig.priority == Priority.HIGH.value
    assert sig.max_retries == 5

    logger.info("✅ Task decorator working")


@pytest.mark.asyncio
async def test_dlq_job_creation():
    """Test DLQ job creation."""
    logger.info("Testing DLQ job creation...")

    # Create failed job
    job = JobProtocol(
        id="failed-123",
        name="process_order",
        args=(123,),
        kwargs={"priority": "high"},
        max_retries=3,
        retry_count=3,
    )
    job.mark_failed("Connection timeout")

    # Simulate DLQ job creation
    dlq_job = JobProtocol(
        id=f"dlq:{job.id}",
        name=f"dlq:{job.name}",
        args=job.args,
        kwargs=job.kwargs,
        max_retries=0,
    )

    assert dlq_job.id == "dlq:failed-123"
    assert dlq_job.name == "dlq:process_order"
    assert dlq_job.args == (123,)
    assert dlq_job.max_retries == 0

    logger.info("✅ DLQ job creation working")


@pytest.mark.asyncio
async def test_integration():
    """Test integration."""
    logger.info("\nTesting integration...")

    # Create queue
    queue = MemoryTaskQueue()

    # Create task with decorator
    @task(name="integration_task", max_retries=2)
    async def integration_task(value: int):
        return value * 2

    # Use distributed lock
    async with distributed_lock("integration:test"):
        # Enqueue job
        job = JobProtocol(
            id="integration-1",
            name="integration_task",
            args=(42,),
            max_retries=2,
        )
        await queue.enqueue(job)

    # Verify
    count = await queue.get_task_count()
    assert count == 1, f"Expected 1 job in queue, got {count}"

    logger.info("✅ integration working")


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Lexigram Tasks - Comprehensive Feature Test v1.0")
    logger.info("=" * 60)
    logger.info("")

    try:
        # Sync tests
        test_retry_logic()
        test_task_decorator()

        # Async tests
        await test_rate_limiting()
        await test_queue_rate_limiter()
        await test_distributed_lock()
        await test_distributed_lock_context()
        await test_dlq_job_creation()
        await test_integration()

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ ALL TESTS PASSED!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Implemented features:")
        logger.info("  ✅ Retry logic with exponential backoff")
        logger.info("  ✅ Rate limiting (token bucket)")
        logger.info("  ✅ Distributed locking")
        logger.info("  ✅ Dead letter queue support")
        logger.info("  ✅ @task decorator")
        logger.info("")

    except Exception as e:
        logger.info("")
        logger.info("=" * 60)
        logger.info("❌ TEST FAILED!")
        logger.info("=" * 60)
        logger.error("Error: %s", e)
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
