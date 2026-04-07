"""WorkerModule — application module definition for the worker process."""

from __future__ import annotations

from lexigram.di.module import Module, module


@module()
class WorkerModule(Module):
    """Root module for the background worker application.

    Imports the WorkerProvider which wires all task handlers, consumers,
    and the DLQ into the DI container.

    Usage::

        from lexigram.app import Application
        from lexigram_example_worker.module import WorkerModule

        app = Application(name="worker")
        app.register_module(WorkerModule)
        await app.start()
    """


__all__ = ["WorkerModule"]
