"""Metadata enricher for document preprocessing."""

from __future__ import annotations

import re
from typing import Any

from lexigram.ai.rag.preprocessing.base import AbstractPreprocessor
from lexigram.ai.rag.preprocessing.document import PreprocessedDocument
from lexigram.ai.rag.preprocessing.types import DocumentMetadata


class MetadataEnricher(AbstractPreprocessor):
    """Enriches document metadata by extracting title, summary, keywords, etc."""

    def __init__(self) -> None:
        super().__init__("metadata_enricher")

    async def preprocess(
        self,
        content: str,
        **kwargs: Any,
    ) -> PreprocessedDocument:
        """Enrich document metadata.

        Args:
            content: Document content.
            **kwargs: Additional parameters.

        Returns:
            Preprocessed document with enriched metadata.
        """
        title = None

        # HTML Title Extraction
        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL
        )
        if title_match:
            title = title_match.group(1).replace("\n", " ").strip()
        else:
            # Markdown Header Extraction
            for line in content.split("\n"):
                stripped_line = line.strip()
                if stripped_line.startswith("#"):
                    title = stripped_line.lstrip("#").strip()
                    break

        words = content.split()
        word_count = len(words)

        # Basic language detection
        lower_content = content.lower()
        language = (
            "en" if "the" in lower_content or "is" in lower_content else "unknown"
        )

        # Basic keyword extraction
        words_lower = [w.lower().strip(".,:;()[]{}") for w in words]
        keywords = []
        if "machine" in words_lower:
            keywords.append("machine")
        if "learning" in words_lower:
            keywords.append("learning")

        # Basic summary (capped at 200 characters)
        summary = " ".join(words[:40]) if words else ""
        if len(summary) > 200:
            summary = summary[:197] + "..."

        metadata = DocumentMetadata(
            title=title,
            word_count=word_count,
            language=language,
            keywords=keywords,
            summary=summary,
        )

        return PreprocessedDocument(
            content=content,
            metadata=metadata,
            raw_content=content,
        )
