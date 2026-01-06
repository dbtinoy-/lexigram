"""
Core document ingestion logic.

Contains the main ingestion processing functionality.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lexigram.ai.workers.document_ingestion.parser import (
    DocumentParser,
    UniversalDocumentParser,
)
from lexigram.ai.workers.document_ingestion.types import (
    ChunkingConfigDict,
    Document,
    IngestionResult,
    IngestionStatus,
)
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.workers.document_ingestion.progress import ProgressTracker
    from lexigram.contracts import VectorStoreProtocol
    from lexigram.contracts.ai.rag import ChunkProtocol
    from lexigram.contracts.ai.vector import ChunkerProtocol

logger = get_logger(__name__)


@dataclass(slots=True)
class _ChunkRecord:
    """Minimal chunk structure used by the ingestion processor."""

    text: str
    metadata: dict[str, Any]
    score: float | None = None


class _SimpleChunker:
    """Fallback chunker used when no chunker implementation is injected."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 200) -> None:
        normalized_chunk_size = max(1, chunk_size)
        normalized_overlap = max(0, overlap)
        self._chunk_size = normalized_chunk_size
        self._overlap = min(normalized_overlap, normalized_chunk_size - 1)

    def chunk(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[_ChunkRecord]:
        if not text:
            return []

        step = max(1, self._chunk_size - self._overlap)
        chunks: list[_ChunkRecord] = []
        index = 0

        for start in range(0, len(text), step):
            end = min(len(text), start + self._chunk_size)
            chunk_text = text[start:end]

            if chunk_text.strip():
                chunk_metadata = dict(metadata or {})
                chunk_metadata.update(
                    {
                        "chunk_index": index,
                        "start_index": start,
                        "end_index": end,
                    }
                )
                chunks.append(_ChunkRecord(text=chunk_text, metadata=chunk_metadata))
                index += 1

            if end >= len(text):
                break

        return chunks


class DocumentProcessor:
    """Handles the core document processing logic."""

    def __init__(
        self,
        vector_store: VectorStoreProtocol,
        progress_tracker: ProgressTracker,
        default_chunking_config: ChunkingConfigDict | None = None,
        chunker: ChunkerProtocol | None = None,
        document_parser: DocumentParser | None = None,
    ):
        """Initialize document processor."""
        self.vector_store = vector_store
        self.progress_tracker = progress_tracker
        self.default_chunking_config = default_chunking_config or {}

        chunk_size = self.default_chunking_config.get("chunk_size", 1000)
        overlap = self.default_chunking_config.get("overlap", 200)
        self._chunker = chunker or _SimpleChunker(
            chunk_size=int(chunk_size),
            overlap=int(overlap),
        )
        self.document_parser = document_parser or UniversalDocumentParser()

    async def process_document(
        self,
        document_id: str,
        file_path: str,
        collection_name: str,
        parser_name: str | None,
        metadata: dict[str, Any],
        batch_size: int = 50,
    ) -> IngestionResult:
        """
        Process a document through the ingestion pipeline.

        This is the main processing function that handles parsing, chunking, and storing.
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Select document parser
            if parser_name:
                logger.info(
                    "Custom parser requested but using default",
                    parser_name=parser_name,
                    document_id=document_id,
                )

            # Update progress: parsing
            await self.progress_tracker.update_progress(
                document_id=document_id,
                status=IngestionStatus.PARSING,
            )

            # Parse document
            document = await self._parse_document(Path(file_path), metadata)
            logger.info(
                "Parsed document",
                document_id=document_id,
                pages=len(document.content.split("\n\n")),
            )

            # Update progress: chunking
            await self.progress_tracker.update_progress(
                document_id=document_id,
                status=IngestionStatus.CHUNKING,
            )

            # Chunk document
            chunks = await self._chunk_document(document)
            logger.info(
                "Chunked document",
                document_id=document_id,
                chunks=len(chunks),
            )

            # Update total chunks
            await self.progress_tracker.update_progress(
                document_id=document_id,
                total_chunks=len(chunks),
            )

            # Update progress: storing
            await self.progress_tracker.update_progress(
                document_id=document_id,
                status=IngestionStatus.STORING,
            )

            # Store chunks in batches
            chunks_created = 0
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]

                await self._store_chunks(batch, collection_name)
                chunks_created += len(batch)

                # Update progress
                await self.progress_tracker.update_progress(
                    document_id=document_id,
                    chunks_processed=chunks_created,
                )

                logger.debug(
                    "Stored chunk batch",
                    document_id=document_id,
                    batch_size=len(batch),
                    total_chunks=chunks_created,
                )

            # Update progress: completed
            await self.progress_tracker.update_progress(
                document_id=document_id,
                status=IngestionStatus.COMPLETED,
            )

            duration = asyncio.get_event_loop().time() - start_time

            logger.info(
                "Document ingestion completed",
                document_id=document_id,
                chunks_created=chunks_created,
                duration=f"{duration:.2f}s",
            )

            return IngestionResult.success_result(
                document_id=document_id,
                chunks_created=chunks_created,
                duration=duration,
                metadata={"collection": collection_name},
            )

        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            error_msg = str(e)

            # Update progress: failed
            await self.progress_tracker.update_progress(
                document_id=document_id,
                error=error_msg,
            )

            logger.exception(
                "Document ingestion failed",
                document_id=document_id,
                error=error_msg,
            )

            return IngestionResult.failure_result(
                document_id=document_id,
                error=error_msg,
                duration=duration,
            )

    async def _parse_document(
        self,
        file_path: Path,
        metadata: dict[str, Any],
    ) -> Document:
        """Parse document from file using configured parser."""
        document = await self.document_parser.parse(file_path)
        document.metadata.update(metadata)
        return document

    async def _chunk_document(self, document: Document) -> list[ChunkProtocol]:
        """Chunk document into smaller pieces."""
        raw_chunks = self._chunker.chunk(document.content, metadata=document.metadata)
        chunks: list[ChunkProtocol] = []

        for index, chunk in enumerate(raw_chunks):
            chunk_text = str(getattr(chunk, "text", ""))
            chunk_metadata = getattr(chunk, "metadata", None)

            merged_metadata = dict(document.metadata)
            if isinstance(chunk_metadata, dict):
                merged_metadata.update(chunk_metadata)
            merged_metadata.setdefault("chunk_index", index)

            chunks.append(
                _ChunkRecord(
                    text=chunk_text,
                    metadata=merged_metadata,
                    score=getattr(chunk, "score", None),
                )
            )

        return chunks

    async def _store_chunks(
        self,
        chunks: list[ChunkProtocol],
        collection_name: str,
    ) -> None:
        """Store chunks in vector store."""
        texts = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        await self.vector_store.add_texts(
            texts=texts,
            metadatas=[m or {} for m in metadatas],
            collection_name=collection_name,
        )
