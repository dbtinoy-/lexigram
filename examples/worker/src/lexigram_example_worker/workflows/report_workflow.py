"""Report generation workflow using a finite state machine.

The :class:`ReportWorkflow` wraps a :class:`~lexigram.workflow.state.machine.StateMachine`
and binds each transition to the corresponding mutation on a
:class:`~lexigram_example_worker.domain.report.Report` aggregate.

State diagram::

    ┌────────┐  start   ┌────────────┐  complete  ┌──────┐
    │ queued │ ──────→  │ processing │ ─────────→ │ done │
    └────────┘          └────────────┘            └──────┘
                               │
                               │ fail
                               ↓
                          ┌────────┐
                          │ failed │
                          └────────┘
"""

from __future__ import annotations

from lexigram.logging import get_logger
from lexigram.workflow.state.machine import StateMachine
from lexigram.workflow.state.models import State, Transition

from lexigram_example_worker.domain.report import Report, ReportStatus

logger = get_logger(__name__)


def _build_state_machine(report: Report) -> StateMachine:
    """Construct a new :class:`StateMachine` wired to *report* mutations.

    Each ``on_enter`` hook updates the report aggregate so the domain model
    stays in sync with the workflow state without coupling the machine to the
    report directly.

    Args:
        report: The :class:`Report` aggregate to track.

    Returns:
        A configured :class:`StateMachine` seeded at the report's current status.
    """

    async def _on_enter_processing() -> None:
        if report.status == ReportStatus.QUEUED:
            report.mark_processing()
        logger.info("report_workflow.processing", report_id=report.id)

    async def _on_enter_done() -> None:
        logger.info("report_workflow.done", report_id=report.id)

    async def _on_enter_failed() -> None:
        logger.warning("report_workflow.failed", report_id=report.id)

    return StateMachine(
        states=[
            State(
                name="queued",
                transitions={
                    "start": Transition(event="start", target="processing"),
                },
            ),
            State(
                name="processing",
                on_enter=_on_enter_processing,
                transitions={
                    "complete": Transition(event="complete", target="done"),
                    "fail": Transition(event="fail", target="failed"),
                },
            ),
            State(
                name="done",
                on_enter=_on_enter_done,
            ),
            State(
                name="failed",
                on_enter=_on_enter_failed,
            ),
        ],
        initial_state=report.status.value,
    )


class ReportWorkflow:
    """Orchestrates the lifecycle of a :class:`~lexigram_example_worker.domain.report.Report`.

    Wraps a :class:`~lexigram.workflow.state.machine.StateMachine` whose
    transitions mirror the :class:`~lexigram_example_worker.domain.report.ReportStatus`
    enum.  Callers drive the workflow via :meth:`start`, :meth:`complete`, and
    :meth:`fail` — the underlying state machine enforces valid sequencing and
    raises :class:`~lexigram.workflow.state.exceptions.StateError` for illegal
    transitions.

    Example::

        workflow = ReportWorkflow(report)
        await workflow.start()          # queued → processing
        await workflow.complete(rows=1234)  # processing → done

    Args:
        report: The report aggregate whose status this workflow manages.
    """

    def __init__(self, report: Report) -> None:
        self._report = report
        self._machine = _build_state_machine(report)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def current_state(self) -> str:
        """Return the workflow's current state name.

        Returns:
            One of ``"queued"``, ``"processing"``, ``"done"``, ``"failed"``.
        """
        return self._machine.current_state

    @property
    def report(self) -> Report:
        """Return the managed :class:`~lexigram_example_worker.domain.report.Report`.

        Returns:
            The report aggregate instance.
        """
        return self._report

    async def start(self) -> None:
        """Advance from ``queued`` to ``processing``.

        Raises:
            StateError: If the machine is not currently in ``queued``.
        """
        await self._machine.transition("start")

    async def complete(self, row_count: int) -> None:
        """Advance from ``processing`` to ``done`` and record *row_count*.

        Args:
            row_count: Number of data rows written to the report output.

        Raises:
            StateError: If the machine is not currently in ``processing``.
        """
        # Transition the machine first — raises StateError for illegal moves.
        await self._machine.transition("complete")
        # Only mutate the aggregate after a successful transition.
        self._report.mark_done(row_count)

    async def fail(self, error_message: str) -> None:
        """Advance from ``processing`` to ``failed`` and record *error_message*.

        Args:
            error_message: Human-readable description of the failure.

        Raises:
            StateError: If the machine is not currently in ``processing``.
        """
        # Transition the machine first — raises StateError for illegal moves.
        await self._machine.transition("fail")
        # Only mutate the aggregate after a successful transition.
        self._report.mark_failed(error_message)

    def can_start(self) -> bool:
        """Return ``True`` when the ``start`` transition is available.

        Returns:
            ``True`` iff the machine is in the ``queued`` state.
        """
        return self._machine.can_transition("start")

    def can_complete(self) -> bool:
        """Return ``True`` when the ``complete`` transition is available.

        Returns:
            ``True`` iff the machine is in the ``processing`` state.
        """
        return self._machine.can_transition("complete")

    def can_fail(self) -> bool:
        """Return ``True`` when the ``fail`` transition is available.

        Returns:
            ``True`` iff the machine is in the ``processing`` state.
        """
        return self._machine.can_transition("fail")


__all__ = ["ReportWorkflow"]
