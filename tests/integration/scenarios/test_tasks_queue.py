"""Tasks in-memory background job processing scenario.

Packages under test: lexigram-tasks
Infrastructure: in-memory task queue (no Redis required)

Scenario:
1. Boot a minimal application with TasksModule using the real in-memory queue.
2. Enqueue a job and assert it executes and its result is stored.
3. Enqueue a job that fails and assert the failure result is recorded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.integration.scenarios._bed import scenario_bed
from tests.integration.scenarios.scenario_apps import create_tasks_app

if TYPE_CHECKING:
    from tests.integration.scenarios._bed import ScenarioTestBed

pytestmark = [pytest.mark.integration, pytest.mark.scenario]


@pytest.fixture
async def bed() -> ScenarioTestBed:
    """Boot a minimal Tasks test application."""
    async with scenario_bed(create_tasks_app) as scenario:
        yield scenario


class TestTasksQueue:
    """Tasks: background job execution and failure result recording."""

    async def test_enqueued_job_executes(self, bed: ScenarioTestBed) -> None:
        """A successfully enqueued job runs to completion."""
        job_id = await bed.tasks.enqueue("send_welcome_email", user_id="u-1")
        result = await bed.tasks.wait(job_id, timeout=10)

        assert result is not None
        assert result.success is True
        assert result.data == {"sent": "u-1"}

    async def test_failed_job_records_failure(self, bed: ScenarioTestBed) -> None:
        """A handler that always fails records a failed result."""
        job_id = await bed.tasks.enqueue("always_fail_task")
        result = await bed.tasks.wait(job_id, timeout=10)

        assert result is not None
        assert result.success is False
        assert result.error is not None
        assert "always fails" in result.error
