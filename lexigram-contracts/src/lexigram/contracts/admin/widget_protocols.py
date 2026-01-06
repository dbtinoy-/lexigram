"""Widget rendering protocols for the admin dashboard.

These protocols define the contract between the admin dashboard shell
and package-level widget contributors. Each package owns its widget
handlers and renderers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lexigram.contracts.admin.errors import AdminError
    from lexigram.contracts.admin.types import WidgetParams
    from lexigram.contracts.core.result import Result

__all__ = ["WidgetHandlerProtocol", "WidgetRendererProtocol"]


@runtime_checkable
class WidgetHandlerProtocol(Protocol):
    """Contract for a single widget data handler.

    Each widget has exactly one handler. The handler fetches data from
    the appropriate service and returns a typed WidgetViewModel.
    Infrastructure exceptions propagate — do not catch them here.

    The return type is intentionally untyped at the protocol level because
    each handler returns its own specific WidgetViewModel frozen dataclass.
    """

    async def get_data(self, params: WidgetParams) -> Result[Any, AdminError]:
        """Fetch widget data and return a typed WidgetViewModel.

        Args:
            params: Parsed widget request parameters.

        Returns:
            Result containing a frozen WidgetViewModel dataclass instance,
            or an AdminError on failure.

        Raises:
            Any infrastructure exception (DB, network, etc.) — not caught.
        """
        ...


@runtime_checkable
class WidgetRendererProtocol(Protocol):
    """Contract for a package-level Jinja2 widget renderer.

    One renderer instance per package (singleton). Owns one
    jinja2.Environment with autoescape=True, auto_reload=False.
    Templates are loaded from the package's widgets/templates/ directory.
    """

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a widget template with a WidgetViewModel context.

        Args:
            template_name: Filename of the Jinja2 template (e.g. "pool_utilization.html").
            context: A dict containing template variables.

        Returns:
            Rendered HTML string.

        Raises:
            jinja2.TemplateNotFound: If template_name does not exist.
        """
        ...
