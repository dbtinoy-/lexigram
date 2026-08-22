"""Boot-level service tests (ratings → stats → regression → report)."""

from __future__ import annotations

import pytest

from feedback_loop.bot import BOT, POOR_KEYS, TRACE_IDS
from feedback_loop.errors import (
    InvalidRatingError,
    UnknownQuestionError,
    UnknownTraceError,
)


async def test_ask_issues_known_trace(service) -> None:
    answer = await service.ask("track-order", owner="alice")

    assert answer.trace_id == TRACE_IDS["track-order"]
    assert answer.answer == BOT["track-order"]


async def test_ask_unknown_question_raises(service) -> None:
    with pytest.raises(UnknownQuestionError):
        await service.ask("nope", owner="alice")


async def test_rate_validates_trace_and_bounds(service) -> None:
    await service.ask("track-order", owner="alice")

    item_id = await service.rate(TRACE_IDS["track-order"], 5, owner="alice")
    assert item_id

    with pytest.raises(UnknownTraceError):
        await service.rate("t9", 5, owner="alice")
    with pytest.raises(InvalidRatingError):
        await service.rate(TRACE_IDS["track-order"], 0, owner="alice")
    with pytest.raises(InvalidRatingError):
        await service.rate(TRACE_IDS["track-order"], 6, owner="alice")


async def test_stats_aggregates_from_memory_mode(service) -> None:
    trace = (await service.ask("warranty", owner="alice")).trace_id
    await service.rate(trace, 2, owner="alice")

    snapshot = await service.stats(owner="alice")

    assert snapshot.total == 1
    assert snapshot.average == 2.0
    assert snapshot.by_type == {"rating": 1}


async def test_regress_promotes_only_low_ratings(service) -> None:
    for key in sorted(BOT):
        await service.ask(key, owner="alice")
    await service.rate(TRACE_IDS["refund-policy"], 1, owner="alice")
    await service.rate(TRACE_IDS["shipping-time"], 2, owner="alice")
    await service.rate(TRACE_IDS["track-order"], 5, owner="alice")
    await service.rate(TRACE_IDS["warranty"], 4, owner="alice")

    summary = await service.regress(owner="alice")

    assert set(summary.failing_ids) == {TRACE_IDS[k] for k in POOR_KEYS}
    assert summary.total_samples == 2
    assert summary.run_id


async def test_regress_run_ids_stable_across_identical_runs(service) -> None:
    for key in sorted(BOT):
        await service.ask(key, owner="alice")
    await service.rate(TRACE_IDS["refund-policy"], 1, owner="alice")
    first = await service.regress(owner="alice")

    await service.rate(TRACE_IDS["shipping-time"], 1, owner="alice")
    second = await service.regress(owner="alice")

    # same experiment name+seed+config ⇒ tracker returns the same run id
    assert second.run_id == first.run_id


async def test_report_matches_run(service) -> None:
    for key in sorted(BOT):
        await service.ask(key, owner="alice")
    await service.rate(TRACE_IDS["refund-policy"], 1, owner="alice")
    await service.rate(TRACE_IDS["shipping-time"], 2, owner="alice")

    summary = await service.regress(owner="alice")
    analysis = await service.report(summary.run_id)

    assert analysis.total_records >= summary.total_samples
    assert analysis.error_count == 0


async def test_regress_without_low_ratings_raises_valueerror(service) -> None:
    await service.ask("track-order", owner="alice")
    await service.rate(TRACE_IDS["track-order"], 5, owner="alice")

    with pytest.raises(ValueError, match="no low-rated"):
        await service.regress(owner="alice")


async def test_degraded_mode_no_database_wiring(service) -> None:
    # the fixture boots without any DatabaseProviderProtocol: collector must
    # stay in memory-buffer mode (that is the demo's intended configuration)
    from lexigram.ai.feedback.services.collector import FeedbackCollector

    collector = service._collector
    assert isinstance(collector, FeedbackCollector)
    assert getattr(collector, "storage", None) is None or not hasattr(
        collector, "storage"
    )
