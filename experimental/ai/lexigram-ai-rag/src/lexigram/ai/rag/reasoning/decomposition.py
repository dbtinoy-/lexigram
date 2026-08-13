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


class QueryDecomposer(AbstractReasoner):
    """Decompose complex queries into simpler sub-queries.

    This reasoner breaks down complex questions into simpler sub-questions
    that can be answered independently, then combines the results.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        vector_store: VectorCollectionProtocol,
        max_sub_queries: int = 5,
        top_k_per_query: int = 2,
        temperature: float = 0.3,
    ):
        """Initialize query decomposer."""
        self.llm_client = llm_client
        self.vector_store = vector_store
        self.max_sub_queries = max_sub_queries
        self.top_k_per_query = top_k_per_query
        self.temperature = temperature

    async def reason(
        self,
        query: str,
        initial_context: list[Any] | None = None,
        **kwargs,
    ) -> ReasoningResult:
        """Perform query decomposition reasoning."""
        # Step 1: Decompose query into sub-queries
        sub_queries = await self._decompose_query(query)

        steps: list[ReasoningStep] = []

        # Step 2: Answer each sub-query
        for i, sub_query in enumerate(sub_queries, 1):
            # Retrieve context for sub-query
            retrieved_docs = await self.vector_store.search(  # type: ignore[call-arg]
                query=sub_query,  # type: ignore[arg-type]
                limit=self.top_k_per_query,
            )

            # Extract text
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

            # Answer sub-query
            answer = await self._answer_sub_query(sub_query, context_texts)

            step = ReasoningStep(
                step_number=i,
                question=sub_query,
                context=retrieved_docs,
                reasoning=f"Sub-query {i} of {len(sub_queries)}",
                answer=answer,
                confidence=0.7,
                metadata={"num_docs": len(retrieved_docs)},
            )
            steps.append(step)

        # Step 3: Synthesize final answer from sub-answers
        final_answer = await self._synthesize_answer(query, steps)

        return ReasoningResult(
            query=query,
            final_answer=final_answer,
            steps=steps,
            strategy=ReasoningStrategy.DECOMPOSITION,
            total_hops=len(steps),
            overall_confidence=0.75,
            metadata={
                "max_sub_queries": self.max_sub_queries,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def _decompose_query(self, query: str) -> list[str]:
        """Decompose complex query into sub-queries."""
        prompt = f"""Break down this complex question into simpler sub-questions that can be answered independently:

Question: {query}

Provide up to {self.max_sub_queries} sub-questions, one per line, numbered:
1. <first sub-question>
2. <second sub-question>
...
"""

        result = await self.llm_client.complete(
            messages=[
                ChatMessage(
                    role="system",
                    content="You are a helpful assistant that breaks down complex questions into simpler sub-questions.",
                ),
                ChatMessage(role="user", content=prompt),
            ],
            temperature=self.temperature,
            max_tokens=300,
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

        # Parse numbered lines
        sub_queries = []
        for raw_line in text.strip().split("\n"):
            line = raw_line.strip()
            # Remove numbering
            if line and (line[0].isdigit() or line.startswith(("-", "•"))):
                # Remove number and dot/dash
                parts = line.split(".", 1) if "." in line else line.split(")", 1)
                sub_query = parts[1].strip() if len(parts) > 1 else line[1:].strip()

                if sub_query:
                    sub_queries.append(sub_query)

        return sub_queries[: self.max_sub_queries]

    async def _answer_sub_query(self, sub_query: str, context: list[str]) -> str:
        """Answer a single sub-query."""
        context_str = "\n\n".join(f"[{i + 1}] {ctx}" for i, ctx in enumerate(context))

        prompt = f"""Context:
{context_str}

Question: {sub_query}

Provide a concise answer based on the context:"""

        result = await self.llm_client.complete(
            messages=[
                ChatMessage(
                    role="system",
                    content="You are a helpful assistant that answers questions based on provided context.",
                ),
                ChatMessage(role="user", content=prompt),
            ],
            temperature=self.temperature,
            max_tokens=200,
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

    async def _synthesize_answer(self, query: str, steps: list[ReasoningStep]) -> str:
        """Synthesize final answer from sub-query answers."""
        prompt = f"Original Question: {query}\n\n"
        prompt += "Sub-question Answers:\n"
        for step in steps:
            prompt += f"{step.step_number}. {step.question}\n"
            prompt += f"   Answer: {step.answer}\n\n"

        prompt += "Based on these sub-question answers, provide a comprehensive answer to the original question:"

        result = await self.llm_client.complete(
            messages=[
                ChatMessage(
                    role="system",
                    content="You are a helpful assistant that synthesizes information from multiple sources.",
                ),
                ChatMessage(role="user", content=prompt),
            ],
            temperature=self.temperature,
            max_tokens=400,
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
