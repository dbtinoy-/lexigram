"""Regression dataset builder tests."""

from __future__ import annotations

from lexigram.contracts.ai.feedback import FeedbackItem, FeedbackType

from feedback_loop.bot import BOT
from feedback_loop.regression import REFERENCE_BARS, ScoredSample, build_dataset


def _item(key: str, rating: float, owner: str = "alice") -> FeedbackItem:
    return FeedbackItem(
        feedback_type=FeedbackType.RATING,
        value=rating,
        owner_id=owner,
        context={
            "trace_id": {"refund-policy": "t1", "shipping-time": "t2",
                         "track-order": "t3", "warranty": "t4"}[key],
            "question_key": key,
            "answer": BOT[key],
            "question": key.replace("-", " "),
        },
    )


class TestBuildDataset:
    def test_low_ratings_promoted(self) -> None:
        dataset = build_dataset([_item("refund-policy", 1), _item("track-order", 5)])

        assert dataset is not None
        assert dataset.name == "regression"
        assert [s.id for s in dataset.samples] == ["t1"]

    def test_threshold_is_inclusive_at_two(self) -> None:
        dataset = build_dataset([_item("shipping-time", 2)])

        assert dataset is not None and len(dataset.samples) == 1

    def test_output_field_present_for_harness(self) -> None:
        dataset = build_dataset([_item("warranty", 1)])
        sample = dataset.samples[0]

        assert sample.output == BOT["warranty"]  # duck-typed attr
        assert sample.reference == REFERENCE_BARS["warranty"]

    def test_empty_when_all_good(self) -> None:
        assert build_dataset([_item("track-order", 5), _item("warranty", 4)]) is None

    def test_scored_sample_shape(self) -> None:
        sample = ScoredSample(id="x", input="q", output="a", reference="r")

        assert hasattr(sample, "output") and sample.metadata == {}
