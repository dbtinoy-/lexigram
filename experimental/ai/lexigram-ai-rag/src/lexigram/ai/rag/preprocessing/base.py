"""
Base preprocessor class for document preprocessing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.ai.rag.preprocessing.document import PreprocessedDocument
else:
    # Forward declaration
    class PreprocessedDocument:
        content: str
        metadata: Any
        raw_content: str | None = None
        preprocessing_stats: dict[str, Any] = {}


class AbstractPreprocessor(ABC):
    """Base class for all document preprocessors.

    All preprocessors should inherit from this class
    to ensure consistent interface and behavior.
    """

    def __init__(self, name: str):
        """Initialize preprocessor.

        Args:
            name: Name of the preprocessor.
        """
        self.name = name

    @abstractmethod
    async def preprocess(
        self,
        content: str,
        **kwargs,
    ) -> PreprocessedDocument:
        """Preprocess document content.

        Args:
            content: Document content to preprocess.
            **kwargs: Additional preprocessing parameters.

        Returns:
            Preprocessed document with extracted information.
        """

    def __repr__(self) -> str:
        """String representation of preprocessor."""
        return f"{self.__class__.__name__}(name='{self.name}')"
