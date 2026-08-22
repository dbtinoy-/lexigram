"""Module for the docs ask demo."""

from __future__ import annotations

import os
from pathlib import Path

from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig
from rag_docs.api import DocsAskApiController
from rag_docs.di.provider import DocsAskProvider
from rag_docs.service import DocsAskService


@module()
class DocsAskModule(Module):
    """Root module: docs ingestion + ask service."""

    @classmethod
    def configure(
        cls, docs_dir: Path | None = None, port: int | None = None
    ) -> DynamicModule:
        selected_port = (
            port if port is not None else int(os.environ.get("RAGDOCS_PORT", "7075"))
        )
        return DynamicModule(
            module=cls,
            imports=[
                WebModule.configure(
                    controllers=[DocsAskApiController],
                    web_config=WebConfig(
                        server=ServerConfig(
                            host="127.0.0.1",
                            port=selected_port,
                        ),
                        # The ask endpoint targets curl/scripts — disable CSRF.
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[DocsAskProvider(docs_dir=docs_dir)],
            exports=[DocsAskService],
        )


__all__ = ["DocsAskModule"]
