"""Observability hook for PromptService.

Apps plug in their own observer to capture render events for A/B testing,
telemetry, or prompt auditing.  The default observer is a no-op.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from lexigram.ai.prompt.rendering.engine import RenderFormat


@runtime_checkable
class PromptObserverProtocol(Protocol):
    """Called by :class:`~lexigram.ai.prompt.service.service.PromptService`
    after every successful render.

    Implement this protocol and pass your instance to
    :class:`~lexigram.ai.prompt.service.service.PromptService` to receive
    render events.

    The call is synchronous and must not raise — any exception will be
    swallowed by the service and logged as a warning.
    """

    def on_render(
        self,
        name: str,
        version: str,
        variables: dict[str, Any],
        rendered_output: str,
        render_format: RenderFormat,
    ) -> None:
        """Invoked after a template is successfully rendered.

        Args:
            name: Template name that was rendered.
            version: Concrete version that was used.
            variables: The resolved variable mapping (post-defaults).
            rendered_output: The final rendered prompt string.
            render_format: The format used to render the template.
        """
        ...


class NoOpPromptObserver:
    """Default no-op observer.  Does nothing on every render event."""

    def on_render(
        self,
        name: str,
        version: str,
        variables: dict[str, Any],
        rendered_output: str,
        render_format: RenderFormat,
    ) -> None:
        """No-op: discard all render events."""


__all__ = ["NoOpPromptObserver", "PromptObserverProtocol"]
