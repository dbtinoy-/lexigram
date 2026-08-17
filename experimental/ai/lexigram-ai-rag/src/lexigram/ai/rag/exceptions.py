"""Exceptions for the RAG package."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import RAGError as _ContractsRAGError
from lexigram.contracts.ai.rag import ChunkingError, RetrievalError, SynthesisError


class RAGError(_ContractsRAGError):
    """Base exception for RAG errors."""

    _code: str = "LEX_ERR_RAG_005"


class PreprocessingError(RAGError):
    """Raised when document preprocessing fails."""

    _code: str = "LEX_ERR_RAG_006"


class MultimodalError(RAGError):
    """Base exception for multimodal processing errors."""

    _code: str = "LEX_ERR_RAG_010"


class AudioLoaderError(MultimodalError):
    """Raised when audio loading fails."""

    _code: str = "LEX_ERR_RAG_011"


class VideoLoaderError(MultimodalError):
    """Raised when video loading fails."""

    _code: str = "LEX_ERR_RAG_012"


class ImageLoaderError(MultimodalError):
    """Raised when image loading fails."""

    _code: str = "LEX_ERR_RAG_013"


class CLIPEmbeddingError(MultimodalError):
    """Raised when CLIP embedding computation fails."""

    _code: str = "LEX_ERR_RAG_014"


class MissingCitationsError(RAGError):
    """Raised when a pipeline with ``require_citations=True`` produces no citations."""

    _code: str = "LEX_ERR_RAG_015"


__all__ = [
    "AudioLoaderError",
    "CLIPEmbeddingError",
    "ChunkingError",
    "ImageLoaderError",
    "MissingCitationsError",
    "MultimodalError",
    "PreprocessingError",
    "RAGError",
    "RetrievalError",
    "SynthesisError",
    "VideoLoaderError",
]
