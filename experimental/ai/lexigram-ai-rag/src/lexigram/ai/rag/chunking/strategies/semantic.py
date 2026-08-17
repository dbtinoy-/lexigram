"""Semantic chunking strategy."""

from __future__ import annotations

import re
from typing import Any

from lexigram.ai.rag.chunking.base import AbstractChunker
from lexigram.ai.rag.chunking.types import Chunk


class SemanticChunker(AbstractChunker):
    """Semantic chunking based on sentence/paragraph boundaries.

    Splits text at natural boundaries (sentences, paragraphs) while respecting
    size constraints.

    Example:
        >>> chunker = SemanticChunker(max_chunk_size=1000)
        >>> chunks = chunker.chunk("Document with sentences...")
    """

    def __init__(
        self,
        max_chunk_size: int = 1000,
        min_chunk_size: int = 100,
        prefer_paragraphs: bool = True,
    ):
        """Initialize semantic chunker.

        Args:
            max_chunk_size: Maximum chunk size in characters
            min_chunk_size: Minimum chunk size (to avoid too-small chunks)
            prefer_paragraphs: Prefer paragraph boundaries over sentences
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.prefer_paragraphs = prefer_paragraphs

        # Sentence boundary pattern
        self.sentence_pattern = re.compile(r"(?<=[.!?])\s+")
        # Paragraph boundary pattern
        self.paragraph_pattern = re.compile(r"\n\n+")

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split text semantically.

        Args:
            text: Text to chunk
            metadata: Optional metadata

        Returns:
            List of chunks
        """
        if not text:
            return []

        chunks: list[Chunk] = []
        chunk_index = 0
        current_chunk: list[str] = []
        current_size: int = 0
        chunk_start: int = 0

        if self.prefer_paragraphs:
            # Split by paragraphs
            paragraphs = self.paragraph_pattern.split(text)
            current_chunk = []
            current_size = 0
            chunk_start = 0

            for raw_para in paragraphs:
                para = raw_para.strip()
                if not para:
                    continue

                # If this paragraph alone exceeds max size, split it by sentences
                if len(para) > self.max_chunk_size:
                    # Save current chunk if any
                    if current_chunk and current_size >= self.min_chunk_size:
                        chunk_text = "\n\n".join(current_chunk)
                        chunks.append(
                            Chunk(
                                text=chunk_text,
                                start_index=chunk_start,
                                end_index=chunk_start + len(chunk_text),
                                chunk_index=chunk_index,
                                metadata=metadata,
                            ),
                        )
                        chunk_index += 1

                    # Split large paragraph by sentences
                    sentences = self.sentence_pattern.split(para)
                    for raw_sent in sentences:
                        sent = raw_sent.strip()
                        if sent and len(sent) >= self.min_chunk_size:
                            chunks.append(
                                Chunk(
                                    text=sent,
                                    start_index=text.find(sent),
                                    end_index=text.find(sent) + len(sent),
                                    chunk_index=chunk_index,
                                    metadata=metadata,
                                ),
                            )
                            chunk_index += 1

                    current_chunk = []
                    current_size = 0
                    chunk_start = text.find(para) + len(para)
                    continue

                # Check if adding this paragraph would exceed size
                if current_size + len(para) > self.max_chunk_size and current_chunk:
                    # Save current chunk
                    if current_size >= self.min_chunk_size:
                        chunk_text = "\n\n".join(current_chunk)
                        chunks.append(
                            Chunk(
                                text=chunk_text,
                                start_index=chunk_start,
                                end_index=chunk_start + len(chunk_text),
                                chunk_index=chunk_index,
                                metadata=metadata,
                            ),
                        )
                        chunk_index += 1

                    current_chunk = [para]
                    current_size = len(para)
                    chunk_start = text.find(para)
                else:
                    current_chunk.append(para)
                    current_size += len(para) + 2  # +2 for \n\n

            # Add remaining chunk
            if current_chunk and current_size >= self.min_chunk_size:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        start_index=chunk_start,
                        end_index=chunk_start + len(chunk_text),
                        chunk_index=chunk_index,
                        metadata=metadata,
                    ),
                )

        else:
            # Split by sentences
            sentences = self.sentence_pattern.split(text)
            current_chunk = []
            current_size = 0
            chunk_start = 0

            for raw_sent in sentences:
                sent = raw_sent.strip()
                if not sent:
                    continue

                if current_size + len(sent) > self.max_chunk_size and current_chunk:
                    if current_size >= self.min_chunk_size:
                        chunk_text = " ".join(current_chunk)
                        chunks.append(
                            Chunk(
                                text=chunk_text,
                                start_index=chunk_start,
                                end_index=chunk_start + len(chunk_text),
                                chunk_index=chunk_index,
                                metadata=metadata,
                            ),
                        )
                        chunk_index += 1

                    current_chunk = [sent]
                    current_size = len(sent)
                    chunk_start = text.find(sent)
                else:
                    current_chunk.append(sent)
                    current_size += len(sent) + 1  # +1 for space

            # Add remaining
            if current_chunk and current_size >= self.min_chunk_size:
                chunk_text = " ".join(current_chunk)
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        start_index=chunk_start,
                        end_index=chunk_start + len(chunk_text),
                        chunk_index=chunk_index,
                        metadata=metadata,
                    ),
                )

        return chunks
