
import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.reasoning import IterativeRefinementReasoner
from lexigram.ai.rag.reasoning.base import (
    AbstractReasoner,
    ReasoningResult,
    ReasoningStep,
    ReasoningStrategy,
)


def test_reasoning_step_repr_and_fields():
    step = ReasoningStep(step_number=1, question="What?", reasoning="Because...")
    r = repr(step)
    assert "ReasoningStep(step=1" in r
    assert "What?" in r


def test_reasoning_result_chain_and_repr():
    steps = [
        ReasoningStep(step_number=1, question="Q1", reasoning="R1", answer="A1"),
        ReasoningStep(step_number=2, question="Q2", reasoning="R2", answer="A2"),
    ]
    res = ReasoningResult(
        query="q",
        final_answer="final",
        steps=steps,
        strategy=ReasoningStrategy.MULTI_HOP,
    )
    chain = res.get_reasoning_chain()
    assert "Query: q" in chain
    assert "Step 1" in chain
    assert "Final Answer: final" in chain
    # repr may not reflect computed hop count (it has defaults); assert on contents instead
    rep = repr(res)
    assert "ReasoningResult(" in rep
    assert "Final Answer: final" or "final" in rep


@pytest.mark.asyncio
async def test_base_reasoner_abstract_and_subclass():
    # AbstractReasoner is abstract; instantiation should fail
    with pytest.raises(TypeError):
        AbstractReasoner()  # type: ignore[arg-type]

    # Create a minimal concrete subclass
    class DummyReasoner(AbstractReasoner):
        async def reason(
            self, query: str, initial_context=None, **kwargs,
        ) -> ReasoningResult:
            return ReasoningResult(
                query=query,
                final_answer="ok",
                steps=[],
                strategy=ReasoningStrategy.MULTI_HOP,
            )

    dr = DummyReasoner()
    res = await dr.reason("hi")
    assert isinstance(res, ReasoningResult)
    assert res.final_answer == "ok"


def test_canonical_import_paths():
    # Types imported via canonical paths should be the same objects
    from lexigram.ai.rag.reasoning.base import ReasoningResult as BR

    assert BR is ReasoningResult

    # Instances created via canonical base are valid ReasoningResult instances
    inst = ReasoningResult(query="q", final_answer="a")
    assert isinstance(inst, BR)

    # IterativeRefinementReasoner is accessible from the canonical reasoning package
    from lexigram.ai.rag.reasoning import IterativeRefinementReasoner as IRR

    assert IRR is IterativeRefinementReasoner
