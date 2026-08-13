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
from lexigram.contracts.data.vector.protocols import VectorCollectionProtocol


class IterativeRefinementReasoner(AbstractReasoner):
    """Iteratively refine answers through multiple passes."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        vector_store: VectorCollectionProtocol,
        max_iterations: int = 3,
        top_k: int = 5,
        temperature: float = 0.5,
    ):
        """Initialize iterative refinement reasoner."""
        self.llm_client = llm_client
        self.vector_store = vector_store
        self.max_iterations = max_iterations
        self.top_k = top_k
        self.temperature = temperature

    async def reason(
        self,
        query: str,
        initial_context: list[Any] | None = None,
        **kwargs,
    ) -> ReasoningResult:
        """Perform iterative refinement reasoning."""
        steps: list[ReasoningStep] = []
        current_answer = ""

        # Initial retrieval
        retrieved_docs = await self.vector_store.search(query=query, limit=self.top_k)  # type: ignore[call-arg,arg-type]

        # Extract context
        context_texts: list[str] = []
        for doc in retrieved_docs:
            if hasattr(doc, "content"):
                text = doc.content
                if text is not None:
                    context_texts.append(text)
            elif isinstance(doc, dict) and "content" in doc:
                context_texts.append(doc["content"])
            elif isinstance(doc, str):
                context_texts.append(doc)

        # Add initial context if provided
        if initial_context:
            for doc in initial_context:
                if hasattr(doc, "content"):
                    text = doc.content
                    if text is not None:
                        context_texts.append(text)
                elif isinstance(doc, dict) and "content" in doc:
                    context_texts.append(doc["content"])
                elif isinstance(doc, str):
                    context_texts.append(doc)

        for iteration in range(1, self.max_iterations + 1):
            if iteration == 1:
                # Initial answer
                answer = await self._generate_initial_answer(query, context_texts)
                reasoning = "Initial answer generation"
            else:
                # Refine previous answer
                answer, critique = await self._refine_answer(
                    query,
                    current_answer,
                    context_texts,
                )
                reasoning = f"Refinement iteration {iteration}: {critique}"

            step = ReasoningStep(
                step_number=iteration,
                question=f"Iteration {iteration}",
                context=retrieved_docs if iteration == 1 else [],
                reasoning=reasoning,
                answer=answer,
                confidence=min(0.5 + (iteration * 0.15), 0.95),
                metadata={"iteration": iteration},
            )
            steps.append(step)
            current_answer = answer

        return ReasoningResult(
            query=query,
            final_answer=current_answer,
            steps=steps,
            strategy=ReasoningStrategy.ITERATIVE_REFINEMENT,
            total_hops=len(steps),
            overall_confidence=steps[-1].confidence if steps else 0.0,
            metadata={
                "max_iterations": self.max_iterations,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def _generate_initial_answer(
        self,
        query: str,
        context: list[str],
    ) -> str:
        """Generate initial answer."""
        context_str = "\n\n".join(f"[{i + 1}] {ctx}" for i, ctx in enumerate(context))

        prompt = f"""Context:
{context_str}

Question: {query}

Provide a comprehensive answer based on the context:"""

        result = await self.llm_client.complete(
            messages=[
                ChatMessage(role="system", content="You are a helpful assistant."),
                ChatMessage(role="user", content=prompt),
            ],
            temperature=self.temperature,
            max_tokens=500,
        )
        if result.is_err():
            raise result.unwrap_err()
        response = result.unwrap()

        # Extract text
        if hasattr(response, "content"):
            return response.content
        if hasattr(response, "choices") and response.choices:
            return response.choices[0].message.content
        if isinstance(response, dict) and "content" in response:
            return response["content"]
        return str(response)

    async def _refine_answer(
        self,
        query: str,
        previous_answer: str,
        context: list[str],
    ) -> tuple[str, str]:
        """Refine previous answer."""
        context_str = "\n\n".join(f"[{i + 1}] {ctx}" for i, ctx in enumerate(context))

        prompt = f"""Question: {query}

Previous Answer:
{previous_answer}

Context:
{context_str}

Please refine the previous answer by:
1. Correcting any inaccuracies
2. Adding missing important information from the context
3. Improving clarity and organization

Provide your critique and refined answer:"""

        result = await self.llm_client.complete(
            messages=[
                ChatMessage(
                    role="system",
                    content="You are a helpful assistant that improves and refines answers.",
                ),
                ChatMessage(role="user", content=prompt),
            ],
            temperature=self.temperature,
            max_tokens=600,
        )
        if result.is_err():
            raise result.unwrap_err()
        response = result.unwrap()

        # Extract text
        if hasattr(response, "content"):
            text = response.content
        elif hasattr(response, "choices") and response.choices:
            text = response.choices[0].message.content
        elif isinstance(response, dict) and "content" in response:
            text = response["content"]
        else:
            text = str(response)

        # Try to separate critique and answer
        if "Refined Answer:" in text:
            parts = text.split("Refined Answer:", 1)
            critique = parts[0].strip()
            answer = parts[1].strip()
        elif "Answer:" in text:
            parts = text.split("Answer:", 1)
            critique = parts[0].strip()
            answer = parts[1].strip()
        else:
            critique = "General refinement"
            answer = text

        return answer, critique
