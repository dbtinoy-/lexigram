"""Tests for column fluent configuration methods (summarizer)."""

from lexigram.ui.columns.types import TextColumn


def test_summarizer_sets_operator():
    col = TextColumn("price").summarizer("sum")
    assert col._summarizer == "sum"


def test_summarizer_average():
    col = TextColumn("rating").summarizer("average")
    assert col._summarizer == "average"


def test_summarizer_defaults_to_none():
    col = TextColumn("price")
    assert col._summarizer is None
