"""Summarise tool — wraps the RAG pipeline as an agent-callable tool.

The :class:`SummariseTool` accepts a plain-text query and returns a
brief summary by running the configured :class:`~lexigram_example_ai.pipelines.rag_pipeline.RAGPipeline`.
It demonstrates how to bridge the :class:`~lexigram.contracts.agents.protocols.ToolProtocol`
interface to an existing pipeline without coupling the pipeline to the
agent framework.

Pattern demonstrated:
- Constructor injection of ``RAGPipeline`` (not the LLM directly)
- ``Result[T, E]`` forwarding from pipeline to tool caller
- Structured logging on entry and exit
"""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import RAGError
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

from lexigram_example_ai.pipelines.rag_pipeline import RAGPipeline, RagQuery

logger = get_logger(__name__)


class SummariseTool:
    """Agent tool that summarises a topic using the RAG pipeline.

    Wraps :class:`~lexigram_example_ai.pipelines.rag_pipeline.RAGPipeline` as
    an agent-invokable tool.  The tool name is used by the agent runtime to
    route ``function_call`` messages.

    Args:
        pipeline: Configured RAG pipeline instance.
        top_k: Number of documents to retrieve per call.
    """

    name: str = "summarise"
    description: str = (
        "Retrieve relevant documents and synthesise a concise summary "
        "answering the provided question."
    )

    def __init__(
        self,
        pipeline: RAGPipeline,
        top_k: int = 3,
    ) -> None:
        self._pipeline = pipeline
        self._top_k = top_k

    async def run(self, query: str) -> Result[str, RAGError]:
        """Execute the RAG pipeline for *query* and return the summary text.

        Args:
            query: The user's question or topic to summarise.

        Returns:
            ``Ok(summary_text)`` on success, ``Err(RAGError)`` on failure.
        """
        logger.info("summarise_tool.run", query_length=len(query), top_k=self._top_k)

        result = await self._pipeline.run(
            RagQuery(query=query, top_k=self._top_k)
        )

        if result.is_err():
            logger.warning(
                "summarise_tool.pipeline_error", error=str(result.unwrap_err())
            )
            return Err(result.unwrap_err())  # type: ignore[arg-type]

        answer = result.unwrap()
        logger.info(
            "summarise_tool.completed",
            sources=len(answer.sources),
            answer_length=len(answer.answer),
        )
        return Ok(answer.answer)


__all__ = ["SummariseTool"]
