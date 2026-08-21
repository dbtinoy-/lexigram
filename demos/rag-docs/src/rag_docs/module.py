"""Module for the docs ask demo."""

from __future__ import annotations

from pathlib import Path

from lexigram.di.module import DynamicModule, Module, module
from rag_docs.di.provider import DocsAskProvider
from rag_docs.service import DocsAskService


@module()
class DocsAskModule(Module):
    """Root module: docs ingestion + ask service."""

    @classmethod
    def configure(cls, docs_dir: Path | None = None) -> DynamicModule:
        return DynamicModule(
            module=cls,
            providers=[DocsAskProvider(docs_dir=docs_dir)],
            exports=[DocsAskService],
        )


__all__ = ["DocsAskModule"]
