
import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.reasoning.base import ReasoningStep
from lexigram.ai.rag.reasoning.chain_of_thought import ChainOfThoughtReasoner
from lexigram.ai.rag.reasoning.multi_hop import MultiHopReasoner


def test_parse_chain_of_thought_simple():
    text = """
    Step 1: Identify the subject
    We see that the subject is 'Foo'.

    Step 2: Determine the date
    The date seems to be 2020 based on the context.

    Therefore, the answer is 2020.
    """

    reasoner = ChainOfThoughtReasoner(None)
    steps = reasoner._parse_chain_of_thought(text)

    assert isinstance(steps, list)
    assert len(steps) >= 2
    assert isinstance(steps[0], ReasoningStep)
    assert "Identify the subject" in steps[0].reasoning


def test_extract_final_answer_with_conclusion_marker():
    text = "Thought 1: Do some work\nTherefore, the answer is 42.\n"
    reasoner = ChainOfThoughtReasoner(None)
    steps = [
        ReasoningStep(step_number=1, question="", reasoning="Do some work", answer=""),
    ]
    ans = reasoner._extract_final_answer(text, steps)
    assert "answer is 42" in ans.lower()


def test_parse_chain_of_thought_fallbacks():
    text = "This is a bit messy.\nNo clear markers, but final line is a conclusion: The capital is Paris."
    reasoner = ChainOfThoughtReasoner(None)
    steps = reasoner._parse_chain_of_thought(text)
    assert isinstance(steps, list)

    ans = reasoner._extract_final_answer(text, steps)
    assert "paris" in ans.lower()


def test_parse_reasoning_response_structured():
    response = (
        "REASONING: We looked at the docs\n"
        "ANSWER: The founder is Elon Musk\n"
        "CONFIDENCE: 0.85\n"
        "IS_FINAL: yes\n"
        "NEXT_QUESTION: N/A\n"
    )

    parser = MultiHopReasoner(None, None)
    result = parser._parse_reasoning_response(response, hop=1)

    assert result["reasoning"].startswith("We looked")
    assert "Elon Musk" in result["answer"]
    assert result["confidence"] == pytest.approx(0.85)
    assert result["is_final"] is True


def test_parse_reasoning_response_missing_fields():
    response = "Some narrative without keys. Could still include an answer."
    parser = MultiHopReasoner(None, None)
    result = parser._parse_reasoning_response(response, hop=1)

    assert isinstance(result, dict)
    assert result["answer"] == ""
    assert result["confidence"] == 0.5
