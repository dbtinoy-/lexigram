
import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.reasoning.parsers import parse_reasoning_response_text


def test_parse_reasoning_response_text_basic():
    text = (
        "REASONING: Some reasoning\n"
        "ANSWER: Foo\n"
        "CONFIDENCE: 0.7\n"
        "IS_FINAL: no\n"
        "NEXT_QUESTION: What next?\n"
    )

    res = parse_reasoning_response_text(text)
    assert res["reasoning"].startswith("Some reasoning")
    assert res["answer"] == "Foo"
    assert res["confidence"] == 0.7
    assert res["is_final"] is False
    assert res["next_question"] == "What next?"
