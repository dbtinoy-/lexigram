from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lexigram.ai.rag.reasoning.base import (
    AbstractReasoner,
    ReasoningResult,
    ReasoningStep,
    ReasoningStrategy,
)
from lexigram.contracts import (
    ChatMessage,
    LLMClientProtocol,
)


class ChainOfThoughtReasoner(AbstractReasoner):
    """Chain-of-thought reasoning for complex queries.

    This reasoner generates explicit reasoning steps before arriving
    at an answer, improving reasoning quality for complex questions.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        max_thoughts: int = 5,
        temperature: float = 0.3,
    ):
        """Initialize chain-of-thought reasoner.

        Args:
            llm_client: LLM client for generation.
            max_thoughts: Maximum number of thoughts to generate.
            temperature: Temperature for LLM generation.
        """
        self.llm_client = llm_client
        self.max_thoughts = max_thoughts
        self.temperature = temperature

    async def reason(
        self,
        query: str,
        initial_context: list[Any] | None = None,
        **kwargs,
    ) -> ReasoningResult:
        """Perform chain-of-thought reasoning without retrieval."""
        context_str = ""
        if initial_context:
            context_texts = []
            for doc in initial_context:
                if hasattr(doc, "content"):
                    context_texts.append(doc.content)
                elif isinstance(doc, dict) and "content" in doc:
                    context_texts.append(doc["content"])
                elif isinstance(doc, str):
                    context_texts.append(doc)

            context_str = "\n\n".join(
                f"[{i + 1}] {ctx}" for i, ctx in enumerate(context_texts)
            )

        return await self.reason_with_context(query, context_str)

    async def reason_with_context(
        self,
        query: str,
        context: str = "",
    ) -> ReasoningResult:
        """Perform chain-of-thought reasoning with given context."""
        prompt = f"Question: {query}\n\n"

        if context:
            prompt += f"Context:\n{context}\n\n"

        prompt += """Please think through this step-by-step and show your reasoning:

Let's approach this systematically:
"""

        result = await self.llm_client.complete(
            messages=[
                ChatMessage(
                    role="system",
                    content="You are a helpful assistant that thinks step-by-step and shows explicit reasoning before answering questions.",
                ),
                ChatMessage(role="user", content=prompt),
            ],
            temperature=self.temperature,
            max_tokens=800,
        )
        if result.is_err():
            raise result.unwrap_err()
        response = result.unwrap()

        # Extract text from response
        if hasattr(response, "content"):
            text = response.content
        elif hasattr(response, "choices") and response.choices:
            text = response.choices[0].message.content
        elif isinstance(response, dict) and "content" in response:
            text = response["content"]
        else:
            text = str(response)

        # Parse thoughts and final answer
        steps = self._parse_chain_of_thought(text)

        # Extract final answer (usually last step or after "Therefore"/"In conclusion")
        final_answer = self._extract_final_answer(text, steps)

        return ReasoningResult(
            query=query,
            final_answer=final_answer,
            steps=steps,
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            total_hops=len(steps),
            overall_confidence=0.8,  # CoT generally has good confidence
            metadata={
                "max_thoughts": self.max_thoughts,
                "has_context": bool(context),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    def _parse_chain_of_thought(self, text: str) -> list[ReasoningStep]:
        """Parse chain of thought into reasoning steps."""
        steps: list[ReasoningStep] = []
        lines = text.strip().split("\n")

        step_markers = ["Step", "Thought", "1.", "2.", "3.", "4.", "5.", "-", "•"]
        current_step = None
        step_num = 0

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            # Check if this starts a new step
            is_step = any(line.startswith(marker) for marker in step_markers)

            if is_step:
                if current_step:
                    steps.append(current_step)

                step_num += 1
                # Remove step marker
                for marker in step_markers:
                    if line.startswith(marker):
                        line = line[len(marker) :].strip()
                        if line.startswith((".", ":")):
                            line = line[1:].strip()
                        break

                current_step = ReasoningStep(
                    step_number=step_num,
                    question="",
                    reasoning=line,
                    answer="",
                    confidence=0.8,
                )
            elif current_step:
                # Continue current step
                current_step.reasoning += " " + line

        # Add last step
        if current_step:
            steps.append(current_step)

        return steps

    def _extract_final_answer(self, text: str, steps: list[ReasoningStep]) -> str:
        """Extract final answer from chain of thought."""
        # Look for conclusion markers
        conclusion_markers = [
            "Therefore,",
            "In conclusion,",
            "The answer is",
            "So,",
            "Thus,",
            "Hence,",
            "Finally,",
        ]

        lines = text.strip().split("\n")
        for i, line in enumerate(lines):
            for marker in conclusion_markers:
                if marker.lower() in line.lower():
                    # Return rest of this line and subsequent lines
                    answer_lines = [line]
                    for j in range(i + 1, min(i + 3, len(lines))):
                        if lines[j].strip():
                            answer_lines.append(lines[j])
                    return " ".join(answer_lines)

        # If no conclusion marker, try to get last substantial sentence
        if steps and steps[-1].reasoning:
            return steps[-1].reasoning

        # Fallback: return last non-empty line
        for line in reversed(lines):
            if line.strip() and len(line) > 20:
                return line.strip()

        return "Unable to extract final answer."
