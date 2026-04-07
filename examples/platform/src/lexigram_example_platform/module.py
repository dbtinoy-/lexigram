"""PlatformModule — application module definition for the platform process."""

from __future__ import annotations

from lexigram.di.module import Module, module


@module()
class PlatformModule(Module):
    """Root module for the multi-tenant SaaS platform application.

    Imports the :class:`~lexigram_example_platform.di.provider.PlatformProvider`
    which wires all domain services, repositories, and the feature-flag manager
    into the DI container.

    Usage::

        from lexigram.app import Application
        from lexigram_example_platform.module import PlatformModule

        app = Application(name="platform")
        app.register_module(PlatformModule)
        await app.start()
    """


__all__ = ["PlatformModule"]
