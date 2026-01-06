from __future__ import annotations

"""Tasks + Queue background job processing scenario.

Packages under test: lexigram-tasks, lexigram-queue
Infrastructure: Redis

Scenario:
1. Boot a minimal application with TasksProvider + QueueProvider (Redis backend).
2. Enqueue a job and assert it executes within a timeout.
3. Enqueue a job that fails transiently and assert it is retried.
4. Enqueue a job that always fails and assert it moves to the dead-letter queue
   after exhausting the configured maximum retry count.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.scenario, pytest.mark.requires_redis]


class TestTasksQueue:
    """Tasks + Queue: background job execution, retries, and dead-letter handling.

    Boots a minimal application with TasksProvider + QueueProvider backed by
    Redis, then exercises job lifecycle including successful execution, transient
    failure with automatic retry, and dead-letter promotion after max retries.
    """

    @pytest.fixture
    async def bed(self) -> None:
        """Boot a minimal Tasks + Queue test application.

        Yields:
            AppTestBed configured with TasksProvider + QueueProvider (Redis).
        """
        pytest.skip(
            "TODO: implement create_tasks_app factory in conftest.py "
            "and wire AppTestBed.from_factory(create_tasks_app)"
        )

    async def test_enqueued_job_executes(self, bed: object) -> None:
        """A successfully enqueued job runs to completion within the timeout.

        The job result (or a side-effect observable via the test bed) must
        be present after the worker drains the queue.

        Args:
            bed: Booted AppTestBed with task queue and live Redis.
        """
        job_id = await bed.tasks.enqueue("send_welcome_email", payload={"user_id": "u-1"})  # type: ignore[attr-defined]
        completed = await bed.tasks.wait_for(job_id, timeout=10)  # type: ignore[attr-defined]

        assert completed is True
        assert await bed.tasks.get_status(job_id) == "completed"  # type: ignore[attr-defined]

    async def test_failed_job_retries(self, bed: object) -> None:
        """A transiently failing job is retried until it succeeds.

        The test bed is configured to make the job fail on the first attempt
        and succeed on the second. After draining the worker the job should
        show status 'completed' with attempt_count >= 2.

        Args:
            bed: Booted AppTestBed with task queue and live Redis.
        """
        # The "flaky_task" handler is pre-configured in the test app to fail
        # once before succeeding.
        job_id = await bed.tasks.enqueue("flaky_task", payload={"fail_times": 1})  # type: ignore[attr-defined]
        completed = await bed.tasks.wait_for(job_id, timeout=30)  # type: ignore[attr-defined]

        assert completed is True
        info = await bed.tasks.get_info(job_id)  # type: ignore[attr-defined]
        assert info["attempt_count"] >= 2
        assert info["status"] == "completed"

    async def test_dead_letter_after_max_retries(self, bed: object) -> None:
        """A persistently failing job is moved to the dead-letter queue.

        After exhausting the maximum configured retry count the job must
        appear in the dead-letter queue and its status must be 'dead'.

        Args:
            bed: Booted AppTestBed with task queue and live Redis.
        """
        # The "always_fail_task" handler raises unconditionally.
        job_id = await bed.tasks.enqueue("always_fail_task", payload={})  # type: ignore[attr-defined]
        await bed.tasks.wait_for(job_id, timeout=60, final_states={"dead", "completed"})  # type: ignore[attr-defined]

        info = await bed.tasks.get_info(job_id)  # type: ignore[attr-defined]
        assert info["status"] == "dead"

        dlq_job_ids = await bed.tasks.list_dead_letter()  # type: ignore[attr-defined]
        assert job_id in dlq_job_ids
