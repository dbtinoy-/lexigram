"""Unit tests for ReportWorkflow state machine."""

from __future__ import annotations

import pytest
from lexigram.workflow.state.exceptions import StateError

from lexigram_example_worker.domain.report import Report, ReportStatus
from lexigram_example_worker.workflows.report_workflow import ReportWorkflow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_report(report_id: str = "rpt-1", name: str = "Sales Q1") -> Report:
    return Report(id=report_id, name=name)


# ---------------------------------------------------------------------------
# Happy-path transitions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workflow_starts_in_queued_state() -> None:
    """Newly created workflow begins in the queued state."""
    report = _new_report()
    workflow = ReportWorkflow(report)

    assert workflow.current_state == "queued"
    assert report.status == ReportStatus.QUEUED


@pytest.mark.asyncio
async def test_start_transitions_to_processing() -> None:
    """start() advances the workflow from queued to processing."""
    report = _new_report()
    workflow = ReportWorkflow(report)

    await workflow.start()

    assert workflow.current_state == "processing"
    assert report.status == ReportStatus.PROCESSING


@pytest.mark.asyncio
async def test_complete_transitions_to_done() -> None:
    """complete() advances from processing to done and records row_count."""
    report = _new_report()
    workflow = ReportWorkflow(report)

    await workflow.start()
    await workflow.complete(row_count=500)

    assert workflow.current_state == "done"
    assert report.status == ReportStatus.DONE
    assert report.row_count == 500
    assert report.completed_at is not None


@pytest.mark.asyncio
async def test_fail_transitions_to_failed() -> None:
    """fail() advances from processing to failed and records the error."""
    report = _new_report()
    workflow = ReportWorkflow(report)

    await workflow.start()
    await workflow.fail("DB connection timeout")

    assert workflow.current_state == "failed"
    assert report.status == ReportStatus.FAILED
    assert report.error_message == "DB connection timeout"
    assert report.completed_at is not None


# ---------------------------------------------------------------------------
# Guard / illegal transition tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cannot_start_from_processing() -> None:
    """start() raises StateError when already in the processing state."""
    report = _new_report()
    workflow = ReportWorkflow(report)
    await workflow.start()

    with pytest.raises(StateError):
        await workflow.start()


@pytest.mark.asyncio
async def test_cannot_complete_from_queued() -> None:
    """complete() raises StateError when called before start()."""
    report = _new_report()
    workflow = ReportWorkflow(report)

    with pytest.raises(StateError):
        await workflow.complete(row_count=0)


@pytest.mark.asyncio
async def test_cannot_fail_from_queued() -> None:
    """fail() raises StateError when called before start()."""
    report = _new_report()
    workflow = ReportWorkflow(report)

    with pytest.raises(StateError):
        await workflow.fail("premature failure")


@pytest.mark.asyncio
async def test_cannot_transition_from_terminal_done_state() -> None:
    """No transitions are possible once the workflow reaches done."""
    report = _new_report()
    workflow = ReportWorkflow(report)
    await workflow.start()
    await workflow.complete(row_count=1)

    with pytest.raises(StateError):
        # Attempt any event from a terminal state
        await workflow.fail("too late")


@pytest.mark.asyncio
async def test_cannot_transition_from_terminal_failed_state() -> None:
    """No transitions are possible once the workflow reaches failed."""
    report = _new_report()
    workflow = ReportWorkflow(report)
    await workflow.start()
    await workflow.fail("initial failure")

    with pytest.raises(StateError):
        await workflow.complete(row_count=0)


# ---------------------------------------------------------------------------
# can_* predicate tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_can_start_only_from_queued() -> None:
    """can_start() returns True only in the queued state."""
    report = _new_report()
    workflow = ReportWorkflow(report)

    assert workflow.can_start() is True
    await workflow.start()
    assert workflow.can_start() is False


@pytest.mark.asyncio
async def test_can_complete_only_from_processing() -> None:
    """can_complete() returns True only in the processing state."""
    report = _new_report()
    workflow = ReportWorkflow(report)

    assert workflow.can_complete() is False
    await workflow.start()
    assert workflow.can_complete() is True
    await workflow.complete(row_count=10)
    assert workflow.can_complete() is False


@pytest.mark.asyncio
async def test_can_fail_only_from_processing() -> None:
    """can_fail() returns True only in the processing state."""
    report = _new_report()
    workflow = ReportWorkflow(report)

    assert workflow.can_fail() is False
    await workflow.start()
    assert workflow.can_fail() is True


# ---------------------------------------------------------------------------
# report property
# ---------------------------------------------------------------------------


def test_workflow_report_property_returns_the_aggregate() -> None:
    """workflow.report returns the same Report instance passed at construction."""
    report = _new_report(report_id="rpt-99")
    workflow = ReportWorkflow(report)

    assert workflow.report is report
    assert workflow.report.id == "rpt-99"
