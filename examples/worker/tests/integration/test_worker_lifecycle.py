"""Integration smoke tests — module import and provider lifecycle.

These tests verify that the worker package imports cleanly and that the
WorkerProvider can register its bindings without any live infrastructure
(all stubs, no Redis / RabbitMQ required).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Import smoke tests
# ---------------------------------------------------------------------------


def test_package_imports_cleanly() -> None:
    """The top-level package must be importable without side-effects."""
    import lexigram_example_worker  # noqa: F401

    assert hasattr(lexigram_example_worker, "WorkerConfig")
    assert hasattr(lexigram_example_worker, "WorkerModule")


def test_domain_imports() -> None:
    """All domain models export correctly."""
    from lexigram_example_worker.domain import (
        Campaign,
        CampaignPayload,
        CampaignQueued,
        Report,
        ReportStatus,
    )

    assert Campaign is not None
    assert CampaignPayload is not None
    assert CampaignQueued is not None
    assert Report is not None
    assert ReportStatus is not None


def test_task_handler_imports() -> None:
    """Task handlers are importable from the tasks subpackage."""
    from lexigram_example_worker.tasks import (
        CleanupOldRecordsHandler,
        GenerateReportHandler,
        SendEmailBatchHandler,
    )

    assert SendEmailBatchHandler is not None
    assert GenerateReportHandler is not None
    assert CleanupOldRecordsHandler is not None


def test_workflow_imports() -> None:
    """Workflow classes import correctly."""
    from lexigram_example_worker.workflows import ReportWorkflow

    assert ReportWorkflow is not None


def test_consumer_imports() -> None:
    """Consumer classes import correctly."""
    from lexigram_example_worker.consumers import CampaignConsumer

    assert CampaignConsumer is not None


def test_provider_imports() -> None:
    """WorkerProvider imports correctly."""
    from lexigram_example_worker.di import WorkerProvider

    assert WorkerProvider is not None


# ---------------------------------------------------------------------------
# WorkerProvider registration lifecycle (no live infra)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_worker_provider_registers_without_error() -> None:
    """WorkerProvider.register() completes without raising against a stub container."""
    from lexigram_example_worker.config import WorkerConfig
    from lexigram_example_worker.di.provider import WorkerProvider

    config = WorkerConfig(queue_driver="memory")
    provider = WorkerProvider(config=config)

    # Minimal stub container that records singleton registrations
    registrations: dict[type, object] = {}

    class StubContainer:
        def singleton(self, interface: type, instance: object, **kwargs: object) -> None:
            registrations[interface] = instance

    await provider.register(StubContainer())  # type: ignore[arg-type]

    # Verify key types were registered
    from lexigram.queue.core.dlq import DeadLetterQueue as MessageDLQ
    from lexigram.tasks.dlq.core import DeadLetterQueue as TaskDLQ
    from lexigram_example_worker.tasks.generate_report import GenerateReportHandler
    from lexigram_example_worker.tasks.send_email_batch import SendEmailBatchHandler

    assert WorkerConfig in registrations
    assert TaskDLQ in registrations
    assert MessageDLQ in registrations
    assert SendEmailBatchHandler in registrations
    assert GenerateReportHandler in registrations


def test_worker_config_defaults() -> None:
    """WorkerConfig has sensible defaults without any environment variables."""
    from lexigram_example_worker.config import WorkerConfig

    config = WorkerConfig()

    assert config.queue_driver == "memory"
    assert config.concurrency == 4
    assert config.dlq_max_size == 10_000
    assert config.dlq_retention_hours == 168.0
    assert config.scheduler_enabled is True


def test_worker_config_cleanup_cron_default() -> None:
    """Cleanup cron defaults to 3am daily."""
    from lexigram_example_worker.config import WorkerConfig

    config = WorkerConfig()

    assert config.cleanup_cron == "0 3 * * *"
