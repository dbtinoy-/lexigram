"""Boot-level service tests (ratings → stats → regression → report)."""

from __future__ import annotations

from lexigram.result import Err, Ok

from feedback_loop.repository.bot import BOT, POOR_KEYS, TRACE_IDS
from feedback_loop.errors import (
    InvalidRatingError,
    UnknownQuestionError,
    UnknownTraceError,
)


async def test_ask_issues_known_trace(service) -> None:
    result = await service.ask("track-order", owner="alice")

    assert isinstance(result, Ok)
    answer = result.unwrap()
    assert answer.trace_id == TRACE_IDS["track-order"]
    assert answer.answer == BOT["track-order"]


async def test_ask_unknown_question_is_err(service) -> None:
    result = await service.ask("nope", owner="alice")

    assert isinstance(result, Err)
    assert isinstance(result.unwrap_err(), UnknownQuestionError)


async def test_rate_validates_trace_and_bounds(service) -> None:
    await service.ask("track-order", owner="alice")

    captured = await service.rate(TRACE_IDS["track-order"], 5, owner="alice")
    assert isinstance(captured, Ok) and captured.unwrap()

    unknown = await service.rate("t9", 5, owner="alice")
    assert isinstance(unknown, Err)
    assert isinstance(unknown.unwrap_err(), UnknownTraceError)

    low = await service.rate(TRACE_IDS["track-order"], 0, owner="alice")
    assert isinstance(low, Err)
    assert isinstance(low.unwrap_err(), InvalidRatingError)

    high = await service.rate(TRACE_IDS["track-order"], 6, owner="alice")
    assert isinstance(high, Err)
    assert isinstance(high.unwrap_err(), InvalidRatingError)


async def test_stats_aggregates_from_memory_mode(service) -> None:
    trace = (await service.ask("warranty", owner="alice")).unwrap().trace_id
    assert (await service.rate(trace, 2, owner="alice")).is_ok()

    snapshot = await service.stats(owner="alice")

    assert snapshot.total == 1
    assert snapshot.average == 2.0
    assert snapshot.by_type == {"rating": 1}


async def test_regress_promotes_only_low_ratings(service) -> None:
    for key in sorted(BOT):
        assert (await service.ask(key, owner="alice")).is_ok()
    await service.rate(TRACE_IDS["refund-policy"], 1, owner="alice")
    await service.rate(TRACE_IDS["shipping-time"], 2, owner="alice")
    await service.rate(TRACE_IDS["track-order"], 5, owner="alice")
    await service.rate(TRACE_IDS["warranty"], 4, owner="alice")

    summary_result = await service.regress(owner="alice")

    assert isinstance(summary_result, Ok)
    summary = summary_result.unwrap()
    assert set(summary.failing_ids) == {TRACE_IDS[k] for k in POOR_KEYS}
    assert summary.total_samples == 2
    assert summary.run_id


async def test_regress_run_ids_stable_across_identical_runs(service) -> None:
    for key in sorted(BOT):
        await service.ask(key, owner="alice")
    await service.rate(TRACE_IDS["refund-policy"], 1, owner="alice")
    first = (await service.regress(owner="alice")).unwrap()

    await service.rate(TRACE_IDS["shipping-time"], 1, owner="alice")
    second = (await service.regress(owner="alice")).unwrap()

    # same experiment name+seed+config ⇒ tracker returns the same run id
    assert second.run_id == first.run_id


async def test_report_matches_run(service) -> None:
    for key in sorted(BOT):
        await service.ask(key, owner="alice")
    await service.rate(TRACE_IDS["refund-policy"], 1, owner="alice")
    await service.rate(TRACE_IDS["shipping-time"], 2, owner="alice")

    summary = (await service.regress(owner="alice")).unwrap()
    analysis = await service.report(summary.run_id)

    assert analysis.total_records >= summary.total_samples
    assert analysis.error_count == 0


async def test_regress_without_low_ratings_is_err(service) -> None:
    from feedback_loop.errors import NoLowRatedError

    await service.ask("track-order", owner="alice")
    await service.rate(TRACE_IDS["track-order"], 5, owner="alice")

    result = await service.regress(owner="alice")

    assert isinstance(result, Err)
    assert isinstance(result.unwrap_err(), NoLowRatedError)


async def test_degraded_mode_no_database_wiring(service) -> None:
    # the fixture boots without any DatabaseProviderProtocol: collector must
    # stay in memory-buffer mode (that is the demo's intended configuration)
    from lexigram.ai.feedback.services.collector import FeedbackCollector

    collector = service._collector
    assert isinstance(collector, FeedbackCollector)
    storage = getattr(collector, "storage", "absent")
    assert storage is None or storage == "absent"
