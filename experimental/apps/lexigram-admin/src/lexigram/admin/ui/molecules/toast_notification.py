"""Fluent toast notification builder (Filament ``Notification::make()`` parity).

Builds a ``ToastData`` for ``ServerToastChannel`` through a chainable API, and
can either render the toast HTML directly or flash it to the admin session for
the next request. This is intentionally distinct from the lifecycle-email
``Notification`` model in ``lexigram.admin.services.notifications`` — it only
concerns the ephemeral admin toast surface.
"""

from __future__ import annotations

from typing import Self

from lexigram.admin.state.context import flash
from lexigram.ui import ServerToastChannel, ToastData, ToastType

_TOAST_CATEGORY = {
    ToastType.SUCCESS: "success",
    ToastType.ERROR: "error",
    ToastType.WARNING: "warning",
    ToastType.INFO: "info",
}


class ToastNotification:
    """Chainable toast builder targeting ``ServerToastChannel``.

    Args:
        message: Default toast message.

    Example:
        ```python
        ToastNotification.make("Resource updated")
            .success()
            .title("Saved")
            .duration(3000)
            .send()

        html = ToastNotification.make("Export queued")
            .info()
            .persistent()
            .actions([{"label": "View", "onclick": "openReport()"}])
            .render()
        ```
    """

    def __init__(self, message: str = "") -> None:
        """Initialize the builder with an empty toast."""
        self._data = ToastData(message=message)

    @classmethod
    def make(cls, message: str = "") -> Self:
        """Start a new toast notification.

        Args:
            message: Initial toast message.

        Returns:
            A new builder instance.
        """
        return cls(message)

    def title(self, title: str) -> Self:
        """Set the toast heading.

        Args:
            title: Heading text.

        Returns:
            The builder for chaining.
        """
        self._data.title = title
        return self

    def message(self, message: str) -> Self:
        """Set the toast body text.

        Args:
            message: Body text.

        Returns:
            The builder for chaining.
        """
        self._data.message = message
        return self

    def icon(self, icon: str | None) -> Self:
        """Override the Lucide icon name for this toast.

        Args:
            icon: Lucide icon name, or ``None`` to use the type default.

        Returns:
            The builder for chaining.
        """
        self._data.icon = icon
        return self

    def success(self) -> Self:
        """Mark the toast as a success notification.

        Returns:
            The builder for chaining.
        """
        self._data.type = ToastType.SUCCESS
        return self

    def error(self) -> Self:
        """Mark the toast as an error notification.

        Returns:
            The builder for chaining.
        """
        self._data.type = ToastType.ERROR
        return self

    def warning(self) -> Self:
        """Mark the toast as a warning notification.

        Returns:
            The builder for chaining.
        """
        self._data.type = ToastType.WARNING
        return self

    def info(self) -> Self:
        """Mark the toast as an informational notification.

        Returns:
            The builder for chaining.
        """
        self._data.type = ToastType.INFO
        return self

    def duration(self, duration_ms: int) -> Self:
        """Set the auto-dismiss delay.

        Args:
            duration_ms: Delay in milliseconds. A non-positive value disables
                auto-dismiss.

        Returns:
            The builder for chaining.
        """
        self._data.duration_ms = max(duration_ms, 0)
        self._data.auto_dismiss = self._data.duration_ms > 0
        return self

    def persistent(self) -> Self:
        """Keep the toast until manually dismissed.

        Returns:
            The builder for chaining.
        """
        self._data.auto_dismiss = False
        self._data.duration_ms = 0
        return self

    def dismissible(self, value: bool = True) -> Self:
        """Set whether the toast shows a dismiss button.

        Args:
            value: Whether the toast can be dismissed by the user.

        Returns:
            The builder for chaining.
        """
        self._data.dismissible = value
        return self

    def actions(self, actions: list[dict[str, str]]) -> Self:
        """Attach action buttons to the toast.

        Args:
            actions: List of ``{"label": ..., "onclick": ...}`` entries.

        Returns:
            The builder for chaining.
        """
        self._data.actions = list(actions)
        return self

    def to_toast(self) -> ToastData:
        """Return the configured ``ToastData`` payload.

        Returns:
            The toast data this builder has configured so far.
        """
        return self._data

    def render(self) -> str:
        """Render the toast as standalone HTML.

        Returns:
            HTML for a single toast element (works inside the toast container).
        """
        return ServerToastChannel().render_toast(self._data)

    def send(self) -> None:
        """Flash the toast to the admin session for the next request.

        Category is derived from the toast type; title/icon/duration are not
        carried by the flash channel, so use :meth:`render` for full fidelity.
        Outside a request context this is a no-op.

        Returns:
            None.
        """
        category = _TOAST_CATEGORY.get(ToastType(self._data.type), "info")
        flash(self._data.title or self._data.message, category)


__all__ = ["ToastNotification"]
