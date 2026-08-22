"""Promote low-rated exchanges into a regression dataset."""

from __future__ import annotations

from dataclasses import dataclass, field

from lexigram.contracts.ai.evaluation import EvaluationDataset
from lexigram.contracts.ai.feedback import FeedbackItem

THRESHOLD_RATING = 2.0

REFERENCE_BARS: dict[str, str] = {
    "refund-policy": "refund within 30 days",
    "shipping-time": "business days",
    "track-order": "tracking id",
    "warranty": "24 month",
}


@dataclass(frozen=True)
class ScoredSample:
    """Mirrors ``EvaluationSample`` plus ``output`` (runner duck-types it)."""

    id: str
    input: str
    output: str
    reference: str
    metadata: dict = field(default_factory=dict)


def build_dataset(items: list[FeedbackItem]) -> EvaluationDataset | None:
    """Collect rated-below-threshold items into samples; None if none.

    Owner filtering happens at the caller (``get_feedback(owner_id=…)``);
    this stays pure over whatever list it receives.
    """
    low = [
        item
        for item in items
        if float(item.value) <= THRESHOLD_RATING
        and {"trace_id", "question_key", "answer"} <= set(item.context)
    ]
    if not low:
        return None
    samples = [
        ScoredSample(
            id=str(item.context["trace_id"]),
            input=str(item.context.get("question", item.context["question_key"])),
            output=str(item.context["answer"]),
            reference=REFERENCE_BARS[str(item.context["question_key"])],
            metadata={},
        )
        for item in low
    ]
    return EvaluationDataset(name="regression", samples=list(samples), metadata={})
