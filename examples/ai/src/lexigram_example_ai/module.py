"""AIModule — application module definition for the AI pipeline example."""

from __future__ import annotations

from lexigram.di.module import Module, module


@module()
class AIModule(Module):
    """Root module for the AI pipeline example application.

    Imports the AIProvider which wires the LLM client, embedding client,
    vector store, chat pipeline, and RAG pipeline into the DI container.

    Usage::

        from lexigram.app import Application
        from lexigram_example_ai.module import AIModule

        app = Application(name="lexigram-example-ai")
        app.register_module(AIModule)
        await app.start()
    """


__all__ = ["AIModule"]
