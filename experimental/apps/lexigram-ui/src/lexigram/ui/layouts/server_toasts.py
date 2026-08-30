"""Toast notification components for admin layout.

Renders toast notifications with HTMX support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from markupsafe import escape

from lexigram.ui.config import ToastConfig


class ToastType(StrEnum):
    """Toast notification types."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ToastData:
    """A toast notification message."""

    message: str
    type: str | ToastType = ToastType.INFO
    title: str | None = None
    icon: str | None = None
    dismissible: bool = True
    auto_dismiss: bool = True
    duration_ms: int = 5000
    id: str | None = None
    actions: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.type, str):
            self.type = ToastType(self.type)


# Default icons for toast types
DEFAULT_ICONS = {
    ToastType.SUCCESS: "check-circle",
    ToastType.ERROR: "x-circle",
    ToastType.WARNING: "alert-triangle",
    ToastType.INFO: "info",
}

# Default colors for toast types
DEFAULT_COLORS = {
    ToastType.SUCCESS: "green",
    ToastType.ERROR: "red",
    ToastType.WARNING: "yellow",
    ToastType.INFO: "blue",
}


class ServerToastChannel:
    """Renders toast notification container and messages (server-driven via HTMX)."""

    def __init__(self, config: ToastConfig | None = None):
        """Initialize the renderer.

        Args:
            config: Toast configuration
        """
        self.config = config or ToastConfig()

    def render(self, toasts: list[ToastData]) -> str:
        """Render toast payloads as HTML.

        Args:
            toasts: List of toast data objects

        Returns:
            HTML string for the toast container with toasts
        """
        return self.render_container(toasts)

    def render_container(self, toasts: list[ToastData] | None = None) -> str:
        """Render the toast container with optional initial toasts.

        Args:
            toasts: List of toast messages to show initially

        Returns:
            HTML string for toast container
        """
        parts: list[str] = []

        position_classes = self._get_position_classes()

        parts.append(f"""
        <div id="toast-container"
             class="toast-container {position_classes}"
             aria-live="polite"
             aria-label="Notifications">
        """)

        # Render initial toasts
        if toasts:
            for toast in toasts[: self.config.max_toasts]:
                parts.append(self.render_toast(toast))

        parts.append("</div>")

        # Add toast handling script
        if self.config.listen_for_events:
            parts.append(self._render_toast_script())

        return "\n".join(parts)

    def render_toast(self, toast: ToastData) -> str:
        """Render a single toast notification.

        Args:
            toast: Toast to render

        Returns:
            HTML string for toast
        """
        toast_type: ToastType = toast.type  # type: ignore[assignment]
        icon = toast.icon or DEFAULT_ICONS.get(toast_type, "info")
        color = DEFAULT_COLORS.get(toast_type, "blue")
        toast_id = toast.id or f"toast-{id(toast)}"

        auto_dismiss_attrs = ""
        if toast.auto_dismiss:
            auto_dismiss_attrs = (
                f'data-auto-dismiss="true" data-duration="{toast.duration_ms}"'
            )

        parts: list[str] = []

        parts.append(f"""
        <div id="{escape(toast_id)}"
             class="toast toast-{escape(toast_type.value)} toast-{escape(color)} show"
             role="alert"
             {auto_dismiss_attrs}>
        """)

        # Icon
        parts.append(f"""
            <div class="toast-icon">
                <i data-lucide="{escape(icon)}" class="w-5 h-5"></i>
            </div>
        """)

        # Content
        parts.append('<div class="toast-content">')

        if toast.title:
            parts.append(f'<div class="toast-title">{escape(toast.title)}</div>')

        parts.append(f'<div class="toast-message">{escape(toast.message)}</div>')

        # Actions
        if toast.actions:
            parts.append('<div class="toast-actions">')
            for action in toast.actions:
                parts.append(f"""
                <button type="button"
                        class="toast-action"
                        onclick="{escape(action.get("onclick", ""))}">
                    {escape(action.get("label", "Action"))}
                </button>
                """)
            parts.append("</div>")

        parts.append("</div>")  # toast-content

        # Dismiss button
        if toast.dismissible:
            parts.append(f"""
            <button type="button"
                    class="toast-dismiss"
                    onclick="dismissToast('{escape(toast_id)}')"
                    aria-label="Dismiss notification">
                <i data-lucide="x" class="w-4 h-4"></i>
            </button>
            """)

        parts.append("</div>")  # toast

        return "\n".join(parts)

    def _get_position_classes(self) -> str:
        """Get CSS classes for toast position."""
        position_map = {
            "top-right": "toast-top toast-right",
            "top-left": "toast-top toast-left",
            "top-center": "toast-top toast-center",
            "bottom-right": "toast-bottom toast-right",
            "bottom-left": "toast-bottom toast-left",
            "bottom-center": "toast-bottom toast-center",
        }
        return position_map.get(self.config.position, "toast-top toast-right")

    def _render_toast_script(self) -> str:
        """Render JavaScript for toast handling."""
        return f"""
        <script>
        // Toast management
        function showToast(options) {{
            const container = document.getElementById('toast-container');
            if (!container) return;

            const toast = document.createElement('div');
            toast.className = 'toast toast-' + (options.type || 'info');
            toast.setAttribute('role', 'alert');

            const iconMap = {{
                success: 'check-circle',
                error: 'x-circle',
                warning: 'alert-triangle',
                info: 'info'
            }};

            toast.innerHTML = `
                <div class="toast-icon">
                    <i data-lucide="${{iconMap[options.type] || 'info'}}" class="w-5 h-5"></i>
                </div>
                <div class="toast-content">
                    ${{options.title ? '<div class="toast-title">' + escapeHtml(options.title) + '</div>' : ''}}
                    <div class="toast-message">${{escapeHtml(options.message)}}</div>
                </div>
                <button type="button" class="toast-dismiss" onclick="this.parentElement.remove()">
                    <i data-lucide="x" class="w-4 h-4"></i>
                </button>
            `;

            container.appendChild(toast);

            // Refresh lucide icons
            if (window.lucide) lucide.createIcons();

            // Auto dismiss
            const duration = options.duration || {self.config.default_duration_ms};
            if (duration > 0) {{
                setTimeout(() => toast.remove(), duration);
            }}
        }}

        function dismissToast(id) {{
            const toast = document.getElementById(id);
            if (toast) toast.remove();
        }}

        // Close a toast by ID from any component via browser event:
        // dispatch(new CustomEvent('lexigram:close-toast', {{ detail: {{ id: 'toast-...' }} }}))
        document.addEventListener('lexigram:close-toast', function(evt) {{
            const id = evt.detail && evt.detail.id;
            if (id) dismissToast(id);
        }});

        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}

        // Listen for HTMX events
        document.addEventListener('htmx:afterRequest', function(evt) {{
            const xhr = evt.detail.xhr;
            const toastHeader = xhr.getResponseHeader('X-Toast');
            if (toastHeader) {{
                try {{
                    const toast = JSON.parse(toastHeader);
                    showToast(toast);
                }} catch (e) {{
                    console.error('Failed to parse toast header:', e);
                }}
            }}
        }});

        // Auto-dismiss initial toasts
        document.querySelectorAll('[data-auto-dismiss="true"]').forEach(toast => {{
            const duration = parseInt(toast.dataset.duration) || {self.config.default_duration_ms};
            setTimeout(() => toast.remove(), duration);
        }});
        </script>
        """


def flash_to_toast(
    flash_messages: list[tuple[str, str]] | None,
) -> list[ToastData]:
    """Convert Flask/Starlette flash messages to toasts.

    Args:
        flash_messages: List of (category, message) tuples

    Returns:
        List of ToastData objects
    """
    if not flash_messages:
        return []

    toasts: list[ToastData] = []

    category_map = {
        "success": ToastType.SUCCESS,
        "error": ToastType.ERROR,
        "danger": ToastType.ERROR,
        "warning": ToastType.WARNING,
        "info": ToastType.INFO,
        "message": ToastType.INFO,
    }

    for category, message in flash_messages:
        toast_type = category_map.get(category.lower(), ToastType.INFO)
        toasts.append(
            ToastData(
                message=message,
                type=toast_type,
            ),
        )

    return toasts


__all__ = [
    "ToastConfig",
    "ToastData",
    "ServerToastChannel",
    "ToastType",
    "flash_to_toast",
]
