"""WorkerProvider — DI composition root for the background worker process.

Wires together:
- :class:`~lexigram.tasks.dlq.core.DeadLetterQueue` (tasks DLQ)
- :class:`~lexigram.queue.core.dlq.DeadLetterQueue` (queue message DLQ)
- :class:`~lexigram_example_worker.tasks.send_email_batch.SendEmailBatchHandler`
- :class:`~lexigram_example_worker.tasks.generate_report.GenerateReportHandler`
- :class:`~lexigram_example_worker.tasks.cleanup_old_records.CleanupOldRecordsHandler`
- :class:`~lexigram_example_worker.consumers.campaign_consumer.CampaignConsumer`

The provider selects the appropriate queue backend from
:class:`~lexigram_example_worker.config.WorkerConfig` so the same code runs
in-process (``memory``) during development and against Redis or RabbitMQ in
production without any application-layer changes (IoC in practice).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from lexigram.contracts.core import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.queue.core.dlq import DeadLetterQueue as MessageDLQ
from lexigram.tasks.dlq.core import DeadLetterQueue as TaskDLQ

from lexigram_example_worker.config import WorkerConfig
from lexigram_example_worker.consumers.campaign_consumer import CampaignConsumer
from lexigram_example_worker.tasks.cleanup_old_records import CleanupOldRecordsHandler
from lexigram_example_worker.tasks.generate_report import GenerateReportHandler
from lexigram_example_worker.tasks.send_email_batch import SendEmailBatchHandler

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


# ---------------------------------------------------------------------------
# Development-only stubs
#
# Replace these with real protocol implementations (e.g. from
# lexigram-notification) by overriding the WorkerProvider.register bindings.
# ---------------------------------------------------------------------------


class _StubMailer:
    """No-op mailer that logs sends instead of delivering real emails."""

    async def send(
        self,
        recipient_id: str,
        subject: str,
        body_html: str,
    ) -> bool:
        logger.debug(
            "stub_mailer.send",
            recipient_id=recipient_id,
            subject=subject,
        )
        return True


class _StubRecordRepository:
    """In-memory record repository that always reports zero deletions."""

    async def delete_older_than(self, cutoff: datetime) -> int:
        logger.debug("stub_record_repository.delete_older_than", cutoff=str(cutoff))
        return 0

logger = get_logger(__name__)


class WorkerProvider(Provider):
    """Composition root — registers and boots all worker-process services.

    Reads :class:`~lexigram_example_worker.config.WorkerConfig` to decide
    which queue backend to activate.  Binds all handlers and the DLQ as
    container singletons so they are available for injection throughout the
    application.

    Args:
        config: Worker configuration.  Defaults to environment-sourced values.
    """

    name = "worker"
    priority = ProviderPriority.NORMAL

    def __init__(self, config: WorkerConfig | None = None) -> None:
        super().__init__()
        self._config = config or WorkerConfig()
        self._consumer: CampaignConsumer | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind all worker services into the container.

        Registrations:
        - :class:`~lexigram_example_worker.config.WorkerConfig` → the loaded config
        - ``TaskDLQ`` → in-memory task dead letter queue
        - ``MessageDLQ`` → in-memory message dead letter queue
        - :class:`~lexigram_example_worker.tasks.send_email_batch.SendEmailBatchHandler`
        - :class:`~lexigram_example_worker.tasks.generate_report.GenerateReportHandler`
        - :class:`~lexigram_example_worker.tasks.cleanup_old_records.CleanupOldRecordsHandler`

        Args:
            container: DI container registrar (provided by the framework).
        """
        container.singleton(WorkerConfig, self._config)

        task_dlq = TaskDLQ(
            max_size=self._config.dlq_max_size,
            retention_hours=self._config.dlq_retention_hours,
        )
        container.singleton(TaskDLQ, task_dlq)

        message_dlq = MessageDLQ(max_size=self._config.dlq_max_size)
        container.singleton(MessageDLQ, message_dlq)

        # Stub mailer — replace with a real MailerProtocol implementation
        # (e.g. from lexigram-notification) in production via the provider.
        mailer = _StubMailer()
        email_handler = SendEmailBatchHandler(mailer=mailer)
        container.singleton(SendEmailBatchHandler, email_handler)

        report_handler = GenerateReportHandler(dlq=task_dlq)
        container.singleton(GenerateReportHandler, report_handler)

        cleanup_handler = CleanupOldRecordsHandler(
            repository=_StubRecordRepository(),
            retention_days=30,
        )
        container.singleton(CleanupOldRecordsHandler, cleanup_handler)

        logger.info(
            "worker_provider.registered",
            queue_driver=self._config.queue_driver,
            dlq_max_size=self._config.dlq_max_size,
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot phase — resolve services and start the campaign consumer.

        The campaign consumer is started here (after the container is frozen)
        so it has access to the fully wired queue backend.

        Args:
            container: DI container resolver (provided by the framework).
        """
        message_dlq = await container.resolve(MessageDLQ)
        email_handler = await container.resolve(SendEmailBatchHandler)

        queue = await self._resolve_queue(container)

        if queue is not None:
            self._consumer = CampaignConsumer(
                queue=queue,
                handler=email_handler,
                dlq=message_dlq,
            )
            await self._consumer.start()
            logger.info("worker_provider.consumer_started")
        else:
            logger.info("worker_provider.no_queue_backend_skipping_consumer")

        logger.info(
            "worker_provider.booted",
            scheduler_enabled=self._config.scheduler_enabled,
        )

    async def shutdown(self) -> None:
        """Gracefully stop the campaign consumer."""
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        logger.info("worker_provider.shutdown")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _resolve_queue(
        self,
        container: ContainerResolverProtocol,
    ) -> object | None:
        """Resolve the queue backend from the container if available.

        Returns ``None`` gracefully when no queue provider is registered
        (e.g. in unit-test environments).

        Args:
            container: DI container resolver.

        Returns:
            Queue backend instance or ``None``.
        """
        from lexigram.contracts.queue.protocols import QueueProtocol

        return await container.resolve_optional(QueueProtocol)


__all__ = ["WorkerProvider"]
