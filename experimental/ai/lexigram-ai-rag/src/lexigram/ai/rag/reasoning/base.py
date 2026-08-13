from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ReasoningStrategy(StrEnum):
    """Available reasoning strategies."""

    MULTI_HOP = "multi_hop"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    DECOMPOSITION = "decomposition"
    ITERATIVE_REFINEMENT = "iterative_refinement"


@dataclass
class ReasoningStep:
    """A single step in the reasoning process.

    Attributes:
        step_number: The step number in the reasoning sequence.
        question: The question being asked in this step.
        context: Retrieved context for this step.
        reasoning: The reasoning or thought process for this step.
        answer: The answer derived from this step.
        confidence: Confidence score for this step (0.0 to 1.0).
        metadata: Additional step metadata.
    """

    step_number: int
    question: str
    context: list[Any] = field(default_factory=list)
    reasoning: str = ""
    answer: str = ""
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ReasoningStep(step={self.step_number}, "
            f"question='{self.question[:50]}...', "
            f"confidence={self.confidence:.2f})"
        )


@dataclass
class ReasoningResult:
    """Result of multi-hop reasoning.

    Attributes:
        query: Original query.
        final_answer: Final answer after all reasoning steps.
        steps: List of reasoning steps taken.
        strategy: Strategy used for reasoning.
        total_hops: Total number of reasoning hops.
        overall_confidence: Overall confidence in the answer.
        metadata: Additional result metadata.
    """

    query: str
    final_answer: str
    steps: list[ReasoningStep] = field(default_factory=list)
    strategy: ReasoningStrategy = ReasoningStrategy.MULTI_HOP
    total_hops: int = 0
    overall_confidence: float = 0.0
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ReasoningResult(hops={self.total_hops}, "
            f"confidence={self.overall_confidence:.2f}, "
            f"answer='{self.final_answer[:50]}...')"
        )

    def get_reasoning_chain(self) -> str:
        """Get full reasoning chain as formatted string."""
        chain = [f"Query: {self.query}\n"]
        for step in self.steps:
            chain.append(f"\nStep {step.step_number}:")
            chain.append(f"  Question: {step.question}")
            chain.append(f"  Reasoning: {step.reasoning}")
            chain.append(f"  Answer: {step.answer}")
            chain.append(f"  Confidence: {step.confidence:.2f}")
        chain.append(f"\nFinal Answer: {self.final_answer}")
        return "\n".join(chain)


class AbstractReasoner(ABC):
    """Base class for reasoning strategies."""

    @abstractmethod
    async def reason(
        self,
        query: str,
        initial_context: list[Any] | None = None,
        **kwargs,
    ) -> ReasoningResult:
        """Perform reasoning on the query.

        Args:
            query: The query to reason about.
            initial_context: Optional initial context.
            **kwargs: Additional strategy-specific parameters.

        Returns:
            ReasoningResult with steps and final answer.
        """
