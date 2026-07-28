"""LLM-based routing strategy."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lexigram.ai.rag.routing.types import (
    DataSource,
    DataSourceType,
    QueryFeatures,
    RoutingDecision,
)
from lexigram.contracts.ai import LLMClientProtocol
from lexigram.contracts.ai.llm import ChatMessage, Role
from lexigram.di.decorators import inject
from lexigram.logging import (
    get_logger,
)
from lexigram.serialization import JSONDecodeError, loads

logger = get_logger(__name__)


@inject
class LLMRouter:
    """LLM-based routing strategy using language models.

    Uses an LLM to analyze queries and make routing decisions based on
    understanding of query intent and data source capabilities.

    Example:
        ```python
        from lexigram.ai.rag import LLMRouter

        async def my_llm_call(prompt):
            # Call your LLM
            return llm.generate(prompt)

        router = LLMRouter(llm_client=my_llm_client)
        decision = await router.route(features, available_sources)
        ```
    """

    ROUTING_PROMPT_TEMPLATE = """You are a query routing expert. Analyze the following query and determine which data sources should be used.

Query: {query}

Query Features:
- Intent: {intent}
- Keywords: {keywords}
- Domain: {domain}
- Complexity: {complexity}
- Modalities: {modalities}

Available Data Sources:
{data_sources}

Instructions:
1. Choose the most appropriate data source(s) from the list above
2. Select a retrieval strategy: dense, sparse, hybrid, multimodal, structured, graph
3. Provide a confidence score (0-1)
4. Explain your reasoning

Respond with a JSON object:
{{
    "data_source_names": ["name1", "name2"],
    "strategy": "dense",
    "confidence": 0.9,
    "reasoning": "explanation here"
}}

Response:"""

    def __init__(
        self,
        *,
        llm_client: LLMClientProtocol | None = None,
        llm_fn: Callable[[str], Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 500,
    ):
        """Initialize the LLM router.

        Args:
            llm_client: Platform LLM client to use for routing.
            llm_fn: Async function to call LLM (fallback if no client).
            temperature: LLM temperature for routing decisions.
            max_tokens: Maximum tokens for LLM response.
        """
        self.llm_client = llm_client
        self.llm_fn = llm_fn
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def route(
        self,
        features: QueryFeatures,
        available_sources: list[DataSource],
    ) -> RoutingDecision:
        """Route query using LLM-based decision making.

        Args:
            features: Extracted query features.
            available_sources: List of available data sources.

        Returns:
            Routing decision from LLM analysis.
        """
        if not self.llm_client and not self.llm_fn:
            return self._fallback_routing(
                features,
                available_sources,
                "No LLM client or function configured",
            )

        if not available_sources:
            return RoutingDecision(
                query=features.text,
                data_sources=[],
                strategy="none",
                confidence=0.0,
                reasoning="No data sources available",
                features=features,
                metadata={"error": "no_sources"},
            )

        # Build prompt
        prompt = self._build_prompt(features, available_sources)

        # Call LLM
        try:
            if self.llm_client:
                # Use platform LLM client
                messages = [
                    ChatMessage(
                        role=Role.USER,
                        content=prompt,
                    ),
                ]
                response_obj = await self.llm_client.complete(
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                # Unwrap Result
                if hasattr(response_obj, "is_err"):
                    if response_obj.is_err():
                        raise response_obj.unwrap_err()
                    response_obj = response_obj.unwrap()  # type: ignore[assignment]
                # Handle both Completion object and raw string
                if hasattr(response_obj, "content"):
                    response = response_obj.content
                elif hasattr(response_obj, "text"):
                    response = response_obj.text
                else:
                    response = str(response_obj)
            else:
                # Use fallback function
                llm_fn = self.llm_fn
                assert llm_fn is not None
                response = await llm_fn(prompt)

            # Parse response
            routing_data = self._parse_llm_response(response)

            # Find selected data sources
            selected_sources = [
                source
                for source in available_sources
                if source.name in routing_data.get("data_source_names", [])
            ]

            if not selected_sources:
                # Use first available if LLM didn't select valid sources
                selected_sources = [available_sources[0]]
                routing_data["reasoning"] += " (Using fallback source)"

            return RoutingDecision(
                query=features.text,
                data_sources=selected_sources,
                strategy=routing_data.get("strategy", "dense"),
                confidence=routing_data.get("confidence", 0.5),
                reasoning=routing_data.get("reasoning", "LLM routing decision"),
                features=features,
                metadata={"llm_routing": True},
            )

        except (ConnectionError, TimeoutError, RuntimeError, ValueError, OSError) as e:
            return self._fallback_routing(
                features,
                available_sources,
                f"LLM routing failed: {e}",
            )

    def _build_prompt(
        self,
        features: QueryFeatures,
        available_sources: list[DataSource],
    ) -> str:
        """Build prompt for LLM routing.

        Args:
            features: Query features.
            available_sources: Available data sources.

        Returns:
            Formatted prompt for LLM.
        """
        # Format data sources
        sources_text = "\n".join(
            [
                f"- {source.name}: {source.description} (type: {source.type.value}, capabilities: {', '.join(source.capabilities)})"
                for source in available_sources
            ],
        )

        # Format modalities
        modalities_text = ", ".join([m.value for m in features.modalities])

        return self.ROUTING_PROMPT_TEMPLATE.format(
            query=features.text,
            intent=features.intent.value,
            keywords=", ".join(features.keywords) if features.keywords else "none",
            domain=features.domain or "general",
            complexity=f"{features.complexity:.2f}",
            modalities=modalities_text,
            data_sources=sources_text,
        )

    def _parse_llm_response(self, response: str) -> dict:
        """Parse LLM response to extract routing decision.

        Args:
            response: LLM response text.

        Returns:
            Parsed routing data.
        """
        # Try to extract JSON from response
        try:
            # Look for JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1

            if start != -1 and end > start:
                json_str = response[start:end]
                return loads(json_str)
        except (JSONDecodeError, ValueError, TypeError) as e:
            logger.debug("Failed to parse LLM response: %s", e)
            # Continue with fallback

        # Fallback: return default
        return {
            "data_source_names": [],
            "strategy": "dense",
            "confidence": 0.3,
            "reasoning": "Failed to parse LLM response",
        }

    def _fallback_routing(
        self,
        features: QueryFeatures,
        available_sources: list[DataSource],
        reason: str,
    ) -> RoutingDecision:
        """Fallback routing when LLM fails.

        Args:
            features: Query features.
            available_sources: Available data sources.
            reason: Reason for fallback.

        Returns:
            Fallback routing decision.
        """
        if available_sources:
            vector_stores = [
                s for s in available_sources if s.type == DataSourceType.VECTOR_STORE
            ]

            fallback_sources = vector_stores or available_sources
            fallback_sources.sort(key=lambda s: s.priority, reverse=True)

            return RoutingDecision(
                query=features.text,
                data_sources=[fallback_sources[0]],
                strategy="dense",
                confidence=0.3,
                reasoning=f"LLM fallback: {reason}",
                features=features,
                metadata={"fallback": True, "reason": reason},
            )

        return RoutingDecision(
            query=features.text,
            data_sources=[],
            strategy="none",
            confidence=0.0,
            reasoning=f"No sources available: {reason}",
            features=features,
            metadata={"error": "no_sources", "reason": reason},
        )
