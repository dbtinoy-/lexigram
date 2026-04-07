"""Generate-report task handler.

Long-running task that:
1. Drives a :class:`~lexigram_example_worker.workflows.report_workflow.ReportWorkflow`
   state machine through ``queued → processing → done | failed``.
2. Simulates CSV row generation (replace with real I/O in production).
3. Routes terminal failures to the injected
   :class:`~lexigram.tasks.dlq.core.DeadLetterQueue` so operators can inspect
   and retry them from the admin panel.

Pattern demonstrated:
- Workflow state machine integration inside a task handler
- DLQ injection for failed-job routing
- ``Result[T, E]`` surfacing both domain and unexpected errors
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.exceptions.domain import DomainError
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.tasks.dlq.core import DeadLetterQueue
from lexigram.tasks.models.job import JobProtocol

from lexigram_example_worker.domain.report import Report
from lexigram_example_worker.workflows.report_workflow import ReportWorkflow

logger = get_logger(__name__)

# Simulated number of rows written per report (replace with real DB query).
_SIMULATED_ROW_COUNT = 1_000


@dataclass(frozen=True)
class ReportRequest:
    """Input data for a single report-generation run.

    Attributes:
        report_id: Identifier of the :class:`~lexigram_example_worker.domain.report.Report`
            to generate.
        report_name: Human-readable name used for logging.
    """

    report_id: str
    report_name: str


@dataclass(frozen=True)
class ReportOutput:
    """Result of a successful report generation.

    Attributes:
        report_id: Identifier of the generated report.
        row_count: Number of rows written to the output.
    """

    report_id: str
    row_count: int


class GenerateReportHandler:
    """Generates a CSV report and advances its workflow state machine.

    Receives a :class:`~lexigram.tasks.dlq.core.DeadLetterQueue` via
    constructor injection.  When generation fails the originating
    :class:`~lexigram.tasks.models.job.JobProtocol` is routed to the DLQ for
    operator inspection and optional retry.

    Args:
        dlq: Dead letter queue for failed report-generation jobs.
    """

    def __init__(self, dlq: DeadLetterQueue) -> None:
        self._dlq = dlq

    async def execute(
        self,
        request: ReportRequest,
        job: JobProtocol | None = None,
    ) -> Result[ReportOutput, DomainError]:
        """Run the report generation pipeline.

        Initialises the :class:`~lexigram_example_worker.domain.report.Report`
        aggregate, drives it through the workflow state machine, performs
        (simulated) data export, and emits structured log lines at each
        transition.

        Args:
            request: Report identifier and name.
            job: Optional originating job reference used for DLQ routing on
                failure.

        Returns:
            ``Ok(ReportOutput)`` on success; ``Err(DomainError)`` on failure.
        """
        report = Report(id=request.report_id, name=request.report_name)
        workflow = ReportWorkflow(report)

        logger.info(
            "generate_report.started",
            report_id=report.id,
            report_name=report.name,
        )

        try:
            await workflow.start()
        except Exception as exc:
            error_msg = f"Failed to start report workflow: {exc}"
            logger.error(
                "generate_report.start_failed",
                report_id=report.id,
                error=error_msg,
            )
            await self._handle_failure(job, report.id, error_msg)
            return Err(DomainError(error_msg))

        # ----------------------------------------------------------------
        # Simulate the actual report generation (replace with real I/O)
        # ----------------------------------------------------------------
        row_count, generation_error = await self._run_generation(report.id)

        if generation_error is not None:
            try:
                await workflow.fail(generation_error)
            except Exception as exc:
                logger.error(
                    "generate_report.fail_transition_error",
                    report_id=report.id,
                    error=str(exc),
                )
            await self._handle_failure(job, report.id, generation_error)
            return Err(DomainError(generation_error))

        try:
            await workflow.complete(row_count=row_count)
        except Exception as exc:
            error_msg = f"Failed to complete report workflow: {exc}"
            logger.error(
                "generate_report.complete_failed",
                report_id=report.id,
                error=error_msg,
            )
            await self._handle_failure(job, report.id, error_msg)
            return Err(DomainError(error_msg))

        output = ReportOutput(report_id=report.id, row_count=row_count)
        logger.info(
            "generate_report.done",
            report_id=report.id,
            row_count=row_count,
        )
        return Ok(output)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _run_generation(self, report_id: str) -> tuple[int, str | None]:
        """Simulate generating report data rows.

        Replace this with real async I/O (database query, S3 upload, etc.)
        in a production implementation.

        Args:
            report_id: Report being generated (used for logging).

        Returns:
            Tuple of ``(row_count, error_message_or_None)``.
        """
        logger.info("generate_report.generating_rows", report_id=report_id)
        # Simulated work — real implementation would stream DB rows → CSV
        row_count = _SIMULATED_ROW_COUNT
        return row_count, None

    async def _handle_failure(
        self,
        job: JobProtocol | None,
        report_id: str,
        error_message: str,
    ) -> None:
        """Route a failed job to the dead letter queue if a job reference exists.

        Args:
            job: Originating job (may be ``None`` for direct handler calls).
            report_id: Report that failed (used for logging).
            error_message: Description of the failure.
        """
        if job is None:
            return
        self._dlq.add(
            job,
            error=error_message,
            report_id=report_id,
        )
        logger.warning(
            "generate_report.routed_to_dlq",
            report_id=report_id,
            job_id=job.id,
            error=error_message,
        )


__all__ = ["GenerateReportHandler", "ReportOutput", "ReportRequest"]
