from __future__ import annotations

from lexigram.ai.rag.query.base import AbstractQueryTransformer, TransformedQuery


class TransformationPipeline:
    """Pipeline for applying multiple query transformations."""

    def __init__(
        self,
        transformers: list[AbstractQueryTransformer],
        combine_results: bool = True,
        max_total_queries: int = 10,
    ):
        self.transformers = transformers
        self.combine_results = combine_results
        self.max_total_queries = max_total_queries

    async def transform(self, query: str) -> list[TransformedQuery]:
        """Apply all transformers to query."""
        results = []
        for transformer in self.transformers:
            result = await transformer.transform(query)
            results.append(result)
        return results

    async def transform_combined(self, query: str) -> list[str]:
        """Apply transformers and combine results."""
        all_results = await self.transform(query)
        combined = []
        seen = set()

        for result in all_results:
            for q in result.transformed:
                if q not in seen:
                    combined.append(q)
                    seen.add(q)
                    if len(combined) >= self.max_total_queries:
                        return combined
        return combined
