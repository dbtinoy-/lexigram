"""Composable RAG pipeline steps.

Individual steps that can be composed into custom RAG workflows using
the pipeline pattern.

Example:
    >>> from lexigram.ai.rag.pipeline import RAGPipeline
    >>> from lexigram.ai.rag.steps.core import (
    ...     LoadDocumentsStep,
    ...     SplitDocumentsStep,
    ...     TranslateStep,  # Custom step!
    ...     IndexDocumentsStep,
    ...     RetrieveContextStep,
    ...     GenerateAnswerStep,
    ... )
    >>>
    >>> # Build custom pipeline with translation
    >>> pipeline = Pipeline("rag-with-translation", [
    ...     LoadDocumentsStep("load", loader),
    ...     SplitDocumentsStep("split", chunker, dependencies=["load"]),
    ...     TranslateStep("translate", to_lang="en", dependencies=["split"]),
    ...     IndexDocumentsStep("index", vector_store, dependencies=["translate"]),
    ...     RetrieveContextStep("retrieve", vector_store, top_k=5),
    ...     GenerateAnswerStep("generate", llm, dependencies=["retrieve"]),
    ... ])
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.chunking.base import AbstractChunker
from lexigram.ai.rag.chunking.types import Chunk
from lexigram.ai.rag.exceptions import (
    RAGError,
)
from lexigram.ai.rag.loaders.core import AbstractDocumentLoader
from lexigram.contracts import (
    DocumentVectorStoreProtocol,
    LLMClientProtocol,
)
from lexigram.contracts.ai.llm import ChatMessage, Completion, Role
from lexigram.contracts.ai.vector import Document, RAGSearchResult
from lexigram.logging import (
    get_logger,
)
from lexigram.primitives.pipeline import PipelineContext, PipelineStep
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


class LoadDocumentsStep(PipelineStep):
    """Load documents from source.

    Stores result in context as 'documents' (list[Chunk]).
    """

    def __init__(
        self,
        name: str,
        loader: AbstractDocumentLoader,
        source_key: str = "source",
        dependencies: list[str] | None = None,
    ):
        """Initialize document loader step."""
        super().__init__(name, dependencies)
        self.loader = loader
        self.source_key = source_key

    async def execute(  # type: ignore[override]
        self, context: PipelineContext
    ) -> Result[list[Chunk], RAGError]:
        """Load documents from source."""
        try:
            source = context.get_step_result(self.source_key)
            if source is None:
                source = context.get_metadata(self.source_key)

            if source is None:
                return Err(
                    RAGError(f"No source found in context key: {self.source_key}"),
                )

            chunks = await self.loader.load(source)
            context.set_step_result(self.name, chunks)
            return Ok(chunks)

        except (ValueError, TypeError, RuntimeError, OSError) as e:
            return Err(RAGError(str(e)))


class SplitDocumentsStep(PipelineStep):
    """Split documents into chunks.

    Expects 'documents' from previous step.
    Stores result as 'chunks' (list[Chunk]).
    """

    def __init__(
        self,
        name: str,
        chunker: AbstractChunker,
        input_key: str = "load",
        dependencies: list[str] | None = None,
    ):
        """Initialize chunking step."""
        super().__init__(name, dependencies)
        self.chunker = chunker
        self.input_key = input_key

    async def execute(  # type: ignore[override]
        self,
        context: PipelineContext,
    ) -> Result[list[Chunk], RAGError]:
        """Split documents into chunks."""
        try:
            documents = context.get_step_result(self.input_key)
            if documents is None:
                return Err(
                    RAGError(f"No documents found from step: {self.input_key}"),
                )

            all_chunks = []
            for doc in documents:
                chunks = self.chunker.chunk(doc.text, doc.metadata)
                all_chunks.extend(chunks)

            context.set_step_result(self.name, all_chunks)
            return Ok(all_chunks)

        except (ValueError, TypeError, RuntimeError, OSError) as e:
            return Err(RAGError(str(e)))


class IndexDocumentsStep(PipelineStep):
    """Index chunks into vector store.

    Expects 'chunks' from previous step.
    Stores result as 'indexed_count' (int).
    """

    def __init__(
        self,
        name: str,
        vector_store: DocumentVectorStoreProtocol,
        input_key: str = "split",
        dependencies: list[str] | None = None,
    ):
        """Initialize indexing step."""
        super().__init__(name, dependencies)
        self.vector_store = vector_store
        self.input_key = input_key

    async def execute(  # type: ignore[override]
        self, context: PipelineContext
    ) -> Result[int, RAGError]:
        """Index chunks into vector store."""
        try:
            chunks = context.get_step_result(self.input_key)
            if chunks is None:
                return Err(RAGError(f"No chunks found from step: {self.input_key}"))

            documents = [
                Document(text=chunk.text, metadata=chunk.metadata) for chunk in chunks
            ]

            add_result = await self.vector_store.add(documents)  # type: ignore[arg-type]
            if add_result.is_err():
                return Err(RAGError(str(add_result.unwrap_err())))

            count = len(documents)
            context.set_step_result(self.name, count)
            return Ok(count)

        except (ValueError, TypeError, RuntimeError, OSError) as e:
            return Err(RAGError(str(e)))


class RetrieveContextStep(PipelineStep):
    """Retrieve relevant context for query.

    Expects 'query' in context metadata.
    Stores result as 'context' (list[RAGSearchResult]).
    """

    def __init__(
        self,
        name: str,
        vector_store: DocumentVectorStoreProtocol,
        top_k: int = 5,
        query_key: str = "query",
        filters_key: str | None = None,
        dependencies: list[str] | None = None,
    ):
        """Initialize retrieval step."""
        super().__init__(name, dependencies)
        self.vector_store = vector_store
        self.top_k = top_k
        self.query_key = query_key
        self.filters_key = filters_key

    async def execute(  # type: ignore[override]
        self,
        context: PipelineContext,
    ) -> Result[list[RAGSearchResult], RAGError]:
        """Retrieve relevant context."""
        try:
            query = context.get_metadata(self.query_key)
            if query is None:
                query = context.get_step_result(self.query_key)

            if query is None:
                return Err(
                    RAGError(f"No query found in context key: {self.query_key}"),
                )

            filters = None
            if self.filters_key:
                filters = context.get_metadata(self.filters_key)

            search_result = await self.vector_store.search(
                query=query,
                top_k=self.top_k,
                filters=filters,
            )

            if search_result.is_err():
                return Err(RAGError(str(search_result.unwrap_err())))

            results = search_result.unwrap()
            context.set_step_result(self.name, results)
            return Ok(results)  # type: ignore[arg-type]

        except (ValueError, TypeError, RuntimeError, OSError) as e:
            return Err(RAGError(str(e)))


class GenerateAnswerStep(PipelineStep):
    """Generate answer from query and context.

    Expects 'query' and 'context' from previous steps.
    Stores result as 'answer' (Completion).
    """

    def __init__(
        self,
        name: str,
        llm: LLMClientProtocol,
        query_key: str = "query",
        context_key: str = "retrieve",
        system_prompt: str | None = None,
        dependencies: list[str] | None = None,
    ):
        """Initialize generation step."""
        super().__init__(name, dependencies)
        self.llm = llm
        self.query_key = query_key
        self.context_key = context_key
        self.system_prompt = system_prompt or (
            "You are a helpful assistant. Answer the question based on the "
            "provided context. If the context doesn't contain relevant "
            "information, say so."
        )

    async def execute(  # type: ignore[override]
        self, context: PipelineContext
    ) -> Result[Any, RAGError]:
        """Generate answer from context."""
        try:
            query = context.get_metadata(self.query_key)
            if query is None:
                query = context.get_step_result(self.query_key)

            retrieved_context = context.get_step_result(self.context_key)

            if query is None:
                return Err(
                    RAGError(f"No query found in context key: {self.query_key}"),
                )

            if retrieved_context is None:
                return Err(
                    RAGError(f"No context found from step: {self.context_key}"),
                )

            context_str = "\n\n".join(
                f"[{i + 1}] {result.document.text}"
                for i, result in enumerate(retrieved_context)
            )

            messages = [
                ChatMessage(role=Role.SYSTEM, content=self.system_prompt),
                ChatMessage(
                    role=Role.USER,
                    content=f"Context:\n{context_str}\n\nQuestion: {query}",
                ),
            ]

            result = await self.llm.complete(messages)
            if result.is_err():
                return Err(RAGError(str(result.unwrap_err())))
            completion = result.unwrap()

            context.set_step_result(self.name, completion)
            return Ok(completion)

        except (ValueError, TypeError, RuntimeError, OSError) as e:
            return Err(RAGError(str(e)))


class TranslationStep(PipelineStep):
    """Example: Translate chunks to target language."""

    def __init__(
        self,
        name: str,
        llm: LLMClientProtocol,
        target_language: str = "English",
        input_key: str = "split",
        dependencies: list[str] | None = None,
    ):
        """Initialize translation step."""
        super().__init__(name, dependencies)
        self.llm = llm
        self.target_language = target_language
        self.input_key = input_key

    async def execute(  # type: ignore[override]
        self, context: PipelineContext
    ) -> Result[list[Chunk], RAGError]:
        """Translate chunks to target language."""
        try:
            chunks = context.get_step_result(self.input_key)
            if chunks is None:
                return Err(RAGError(f"No chunks found from step: {self.input_key}"))

            translated_chunks = []
            for chunk in chunks:
                messages = [
                    ChatMessage(
                        role=Role.USER,
                        content=f"Translate to {self.target_language}:\n\n{chunk.text}",
                    ),
                ]

                raw_completion = await self.llm.complete(messages)

                if isinstance(raw_completion, Err):
                    return Err(RAGError(str(raw_completion.unwrap_err())))

                completion_obj = raw_completion.unwrap()
                if isinstance(completion_obj, str):
                    completion_obj = Completion(  # type: ignore[assignment]
                        content=completion_obj,
                        model=getattr(self.llm, "model", "unknown"),
                    )

                translated_chunk = Chunk(
                    text=completion_obj.content,
                    source=chunk.source,
                    chunk_index=chunk.chunk_index,
                    metadata={
                        **chunk.metadata,
                        "translated": True,
                        "target_language": self.target_language,
                        "original_content": chunk.text,
                    },
                )
                translated_chunks.append(translated_chunk)

            context.set_step_result(self.name, translated_chunks)
            return Ok(translated_chunks)

        except (ValueError, TypeError, RuntimeError, OSError) as e:
            return Err(RAGError(str(e)))
