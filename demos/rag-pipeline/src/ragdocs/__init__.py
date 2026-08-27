"""RAG pipeline demo — document ingestion and retrieval.

Convention followed: **Package exports** — ``__init__.py`` re-exports
the public API surface without defining logic.

Exports:

- ``create_app`` — composition root for the application
- ``RagDocsConfig`` — demo configuration model
- ``RagDocsProvider`` — DI provider for RAG pipeline services
"""

from __future__ import annotations

from ragdocs.app import create_app
from ragdocs.config import RagDocsConfig
from ragdocs.di.provider import RagDocsProvider

__all__ = [
    "RagDocsConfig",
    "RagDocsProvider",
    "create_app",
]
