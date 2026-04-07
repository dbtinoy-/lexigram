"""UI module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.di.module import DynamicModule, Module, module
from lexigram.ui.protocols import RenderableProtocol


@module()
class UIModule(Module):
    """HTMX/htpy component library module.

    Call :meth:`configure` to configure and register the UI component
    system for injection.

    Usage::

        from lexigram.ui.config import UIConfig

        @module(
            imports=[UIModule.configure(UIConfig(default_theme="default"))]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(cls, config: Any | None = None, **kwargs: Any) -> DynamicModule:
        """Create a UIModule with explicit configuration.

        Args:
            config: :class:`~lexigram.ui.config.UIConfig` or ``None``
                to use defaults.
            **kwargs: Additional keyword arguments forwarded to
                :class:`~lexigram.ui.di.provider.UIProvider`.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ui.di.provider import UIProvider

        return DynamicModule(
            module=cls,
            providers=[UIProvider(config=config, **kwargs)],
            exports=[RenderableProtocol],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return a no-op UIModule for testing.

        Registers the UI provider with default configuration.
        No real rendering backends are configured.

        Args:
            config: Optional UIConfig override (passed to UIProvider).

        Returns:
            A DynamicModule with default UI configuration.
        """
        from lexigram.ui.di.provider import UIProvider

        return DynamicModule(
            module=cls,
            providers=[UIProvider(config=config)],
            exports=[RenderableProtocol],
        )


__all__ = ["UIModule"]
