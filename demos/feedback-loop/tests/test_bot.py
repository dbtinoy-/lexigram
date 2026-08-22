"""Bot registry surface tests."""

from __future__ import annotations

import pytest

from lexigram.contracts.exceptions.domain import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from feedback_loop.repository.bot import BOT, POOR_KEYS, TRACE_IDS
from feedback_loop.errors import (
    InvalidRatingError,
    NoLowRatedError,
    UnknownQuestionError,
    UnknownTraceError,
)


class TestBot:
    def test_four_questions_two_poor(self) -> None:
        assert len(BOT) == 4
        assert POOR_KEYS == {"refund-policy", "shipping-time"}

    def test_trace_ids_stable_and_unique(self) -> None:
        assert sorted(TRACE_IDS.values()) == ["t1", "t2", "t3", "t4"]
        assert set(TRACE_IDS) == set(BOT)

    def test_poor_answers_miss_reference_bars(self) -> None:
        assert "tracking" not in BOT["shipping-time"].lower()
        assert "24 month" not in BOT["refund-policy"].lower()


class TestErrors:
    def test_error_hierarchy(self) -> None:
        assert issubclass(InvalidRatingError, ValidationError)
        assert issubclass(UnknownQuestionError, NotFoundError)
        assert issubclass(UnknownTraceError, NotFoundError)
        assert issubclass(NoLowRatedError, ConflictError)
