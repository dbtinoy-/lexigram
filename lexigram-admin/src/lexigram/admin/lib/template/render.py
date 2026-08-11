"""Template utilities for lexigram-admin.

Provides simple template rendering functions for standalone pages
like login, error, etc. Uses StandaloneLayout for consistent styling.
"""

from typing import Any

from markupsafe import escape

from lexigram.admin.ui.layouts import (
    StandaloneLayout,
    StandaloneLayoutConfig,
    StandaloneLayoutContext,
)


def render_template(
    template_name: str,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> str:
    """Render a named template.

    This is a simple fallback template renderer. For full template support,
    use the Jinja2 integration in ui/templates_jinja.py.

    Args:
        template_name: Template name (used as title)
        context: Template context
        **kwargs: Additional context values

    Returns:
        HTML string
    """
    ctx = context or {}
    ctx.update(kwargs)

    title = ctx.get("title", template_name)
    content = ctx.get("content", "")

    # Include debug info when error template is requested
    if template_name == "debug_error.html":
        exc_type = ctx.get("exc_type", "")
        exc_message = ctx.get("exc_message", "")
        traceback = ctx.get("traceback", "")
        traceback_plain = ctx.get("traceback_plain", "")
        debug_html = f"""
        <div class="error-details" style="margin-top: 1rem; padding: 1rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 4px;">
            <h2 style="color: #b91c1c;">{escape(str(exc_type))}</h2>
            <pre style="white-space: pre-wrap; word-break: break-word; font-family: monospace; font-size: 0.85rem; margin-top: 0.5rem;">{escape(str(exc_message))}</pre>
            <details style="margin-top: 0.5rem;">
                <summary style="cursor: pointer; font-weight: 500;">Traceback</summary>
                <pre style="white-space: pre-wrap; word-break: break-word; font-family: monospace; font-size: 0.75rem; max-height: 400px; overflow: auto; margin-top: 0.25rem; background: #1f2937; color: #e5e7eb; padding: 0.75rem; border-radius: 4px;">{escape(str(traceback_plain))}</pre>
            </details>
        </div>
        """
        content = debug_html

    config = StandaloneLayoutConfig(
        show_footer=False,
        show_logo=False,
        centered=False,
    )
    layout_context = StandaloneLayoutContext(
        page_title=title,
    )

    page_content = f"""
    <main class="container" style="padding: 2rem;">
        <h1>{escape(title)}</h1>
        {content}
    </main>
    """

    layout = StandaloneLayout(config=config, context=layout_context)
    return layout.render(page_content)
