"""
Simplified preprocessing pipeline after modular refactoring.

Keeps only the essential pipeline functionality.
"""

from __future__ import annotations

from lexigram.ai.rag.preprocessing.base import AbstractPreprocessor
from lexigram.ai.rag.preprocessing.document import PreprocessedDocument
from lexigram.ai.rag.preprocessing.types import DocumentType


class PreprocessingPipeline:
    """Simplified document preprocessing pipeline.

    Provides a clean interface for document preprocessing
    with support for OCR, table extraction, and metadata enrichment.
    """

    def __init__(self, preprocessors: list[AbstractPreprocessor] | None = None):
        """Initialize preprocessing pipeline.

        Args:
            preprocessors: List of preprocessors to run in sequence.
        """
        self.preprocessors = preprocessors or []

    def add_preprocessor(self, preprocessor: AbstractPreprocessor) -> None:
        """Add a preprocessor to the pipeline.

        Args:
            preprocessor: Preprocessor to add.
        """
        self.preprocessors.append(preprocessor)

    async def process(
        self,
        content: str,
        doc_type: DocumentType = DocumentType.UNKNOWN,
        **kwargs,
    ) -> PreprocessedDocument:
        """Process document through pipeline.

        Args:
            content: Document content to process.
            doc_type: Type of document (auto-detected if unknown).
            **kwargs: Additional processing parameters.

        Returns:
            Preprocessed document with extracted information.
        """
        current_content = content
        current_metadata = None
        images = []
        tables = []

        # Run each preprocessor in sequence
        for preprocessor in self.preprocessors:
            result = await preprocessor.preprocess(current_content, **kwargs)
            current_content = result.content
            if not current_metadata:
                current_metadata = result.metadata
            # Merge metadata
            elif hasattr(current_metadata, "merge"):
                current_metadata.merge(result.metadata)

            if hasattr(result, "images") and result.images:
                images.extend(result.images)
            if hasattr(result, "tables") and result.tables:
                tables.extend(result.tables)

        if not self.preprocessors:
            return PreprocessedDocument(content=content, raw_content=content)

        return PreprocessedDocument(
            content=current_content,
            metadata=current_metadata,
            raw_content=content,
            images=images,
            tables=tables,
        )

    async def process_batch(
        self,
        documents: list[tuple[str, DocumentType]],
        **kwargs,
    ) -> list[PreprocessedDocument]:
        """Process multiple documents in parallel.

        Args:
            documents: List of (content, doc_type) tuples.
            **kwargs: Additional processing parameters.

        Returns:
            List of preprocessed documents.
        """
        import asyncio

        tasks = [
            self.process(content, doc_type, **kwargs) for content, doc_type in documents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        processed = []
        for result in results:
            if isinstance(result, BaseException):
                raise result
            processed.append(result)
        return processed
