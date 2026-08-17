"""Multi-hop reasoner implementation split into its own module.

This module contains the concrete MultiHopReasoner implementation and
convenience entrypoint `multi_hop_reason`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from lexigram.ai.rag.reasoning.base import (
    AbstractReasoner,
    ReasoningResult,
    ReasoningStep,
    ReasoningStrategy,
)
from lexigram.contracts import ChatMessage

if TYPE_CHECKING:
    from lexigram.contracts import LLMClientProtocol
    from lexigram.contracts.data.vector.protocols import (
        VectorCollectionProtocol,
        VectorStoreProtocol,
    )


class MultiHopReasoner(AbstractReasoner):
    """Multi-hop reasoning over multiple retrieval steps.

    This reasoner breaks down complex queries into multiple hops,
    where each hop retrieves relevant information and builds upon
    previous steps.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        vector_store: VectorCollectionProtocol,
        max_hops: int = 3,
        top_k_per_hop: int = 3,
        confidence_threshold: float = 0.5,
        temperature: float = 0.3,
    ):
        self.llm_client = llm_client
        self.vector_store = vector_store
        self.max_hops = max_hops
        self.top_k_per_hop = top_k_per_hop
        self.confidence_threshold = confidence_threshold
        self.temperature = temperature

    async def reason(
        self,
        query: str,
        initial_context: list[Any] | None = None,
        **kwargs,
    ) -> ReasoningResult:
        steps: list[ReasoningStep] = []
        current_query = query
        accumulated_knowledge = []

        if initial_context:
            accumulated_knowledge.extend(initial_context)

        for hop in range(1, self.max_hops + 1):
            retrieved_docs = await self.vector_store.search(  # type: ignore[call-arg]
                query=current_query,  # type: ignore[arg-type]
                limit=self.top_k_per_hop,
            )

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

            reasoning_prompt = self._build_reasoning_prompt(
                original_query=query,
                current_query=current_query,
                context=context_texts,
                previous_steps=steps,
                hop_number=hop,
            )

            result = await self.llm_client.complete(
                messages=[
                    ChatMessage(
                        role="system",
                        content="You are a helpful assistant that performs step-by-step reasoning to answer complex questions.",
                    ),
                    ChatMessage(role="user", content=reasoning_prompt),
                ],
                temperature=self.temperature,
                max_tokens=500,
            )
            if result.is_err():
                raise result.unwrap_err()
            response = result.unwrap()

            step_result = self._parse_reasoning_response(response, hop)

            step = ReasoningStep(
                step_number=hop,
                question=current_query,
                context=retrieved_docs,
                reasoning=step_result.get("reasoning", ""),
                answer=step_result.get("answer", ""),
                confidence=step_result.get("confidence", 0.5),
                metadata={
                    "num_docs": len(retrieved_docs),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )
            steps.append(step)

            accumulated_knowledge.append(step.answer)

            if step_result.get("is_final", False):
                break

            if step.confidence < self.confidence_threshold:
                break

            next_query = step_result.get("next_question")
            if not next_query or next_query == current_query:
                break

            current_query = next_query

        final_answer = await self._generate_final_answer(query, steps)

        overall_confidence = (
            sum(step.confidence for step in steps) / len(steps) if steps else 0.0
        )

        return ReasoningResult(
            query=query,
            final_answer=final_answer,
            steps=steps,
            strategy=ReasoningStrategy.MULTI_HOP,
            total_hops=len(steps),
            overall_confidence=overall_confidence,
            metadata={
                "max_hops": self.max_hops,
                "top_k_per_hop": self.top_k_per_hop,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    def _build_reasoning_prompt(
        self,
        original_query: str,
        current_query: str,
        context: list[str],
        previous_steps: list[ReasoningStep],
        hop_number: int,
    ) -> str:
        prompt = f"Original Question: {original_query}\n\n"

        if previous_steps:
            prompt += "Previous Reasoning Steps:\n"
            for step in previous_steps:
                prompt += f"Step {step.step_number}: {step.question}\n"
                prompt += f"Answer: {step.answer}\n\n"

        prompt += f"Current Question (Step {hop_number}): {current_query}\n\n"

        prompt += "Retrieved Context:\n"
        for i, ctx in enumerate(context, 1):
            prompt += f"[{i}] {ctx}\n\n"

        prompt += """Please analyze this step and provide:
1. Your reasoning about what information is relevant
2. An answer to the current question based on the context
3. A confidence score (0.0 to 1.0)
4. Whether this is the final answer or if more steps are needed
5. If not final, what the next question should be

Format your response as:
REASONING: <your reasoning>
ANSWER: <answer to current question>
CONFIDENCE: <0.0-1.0>
IS_FINAL: <yes/no>
NEXT_QUESTION: <next question if not final>
"""
        return prompt

    def _parse_reasoning_response(self, response: Any, hop: int) -> dict:
        """Extract text from a provider response and parse it using the
        shared parsing helper in `reasoning.parsers`.
        """
        if hasattr(response, "content"):
            text = response.content
        elif hasattr(response, "choices") and response.choices:
            text = response.choices[0].message.content
        elif isinstance(response, dict) and "content" in response:
            text = response["content"]
        else:
            text = str(response)

        # Import locally to avoid circular import during package initialization
        from lexigram.ai.rag.reasoning.parsers import parse_reasoning_response_text

        return parse_reasoning_response_text(text)

    async def _generate_final_answer(
        self,
        query: str,
        steps: list[ReasoningStep],
    ) -> str:
        if not steps:
            return "Unable to answer the question with available information."

        if steps[-1].answer:
            return steps[-1].answer

        return "Unable to generate final answer."


async def multi_hop_reason(
    query: str,
    llm_client: LLMClientProtocol,
    vector_store: VectorStoreProtocol,
    strategy: ReasoningStrategy = ReasoningStrategy.MULTI_HOP,
    **kwargs,
) -> ReasoningResult:
    from lexigram.ai.rag.reasoning.strategy_registry import (
        ReasoningStrategyRegistry,
    )

    registry = ReasoningStrategyRegistry.with_defaults()
    return await registry.reason(
        strategy,
        llm_client,
        vector_store,  # type: ignore[arg-type]
        query,
        kwargs,
    )
