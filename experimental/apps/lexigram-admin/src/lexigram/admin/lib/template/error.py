"""Template utilities for lexigram-admin.

Provides simple template rendering functions for standalone pages
like login, error, etc. Uses StandaloneLayout for consistent styling.
"""

from markupsafe import escape

from lexigram.admin.ui.layouts import (
    StandaloneLayout,
    StandaloneLayoutConfig,
    StandaloneLayoutContext,
)


def render_error_page(
    status_code: int = 500,
    title: str = "Error",
    message: str = "An error occurred",
    details: str = "",
    site_name: str = "Lexigram Admin",
    icon: str = "",
    action_text: str = "Return to Admin",
    action_url: str = "/admin/",
    base_url: str = "/admin",
) -> str:
    """Render a standalone error page.

    Args:
        status_code: HTTP status code
        title: Error title
        message: Error message
        details: Additional details (hidden in production)
        site_name: Site name for branding
        icon: Emoji icon to display
        action_text: Call-to-action button text
        action_url: Call-to-action button URL
        base_url: Mounted admin base URL used for shared assets.

    Returns:
        HTML string for error page
    """
    config = StandaloneLayoutConfig(
        app_name=site_name,
        show_footer=True,
        centered=True,
    )
    context = StandaloneLayoutContext(
        page_title=title,
        base_url=base_url,
    )

    details_html = ""
    if details:
        details_html = f"""
        <details class="text-left mt-4">
            <summary class="cursor-pointer font-medium text-sm text-muted-foreground">Technical Details</summary>
            <pre class="bg-muted text-foreground p-4 rounded-md overflow-x-auto mt-2">{escape(details)}</pre>
        </details>
        """

    icon_html = (
        f'<div style="font-size: 3rem; margin-bottom: 0.5rem;">{icon}</div>'
        if icon
        else ""
    )

    content = f"""
    <div class="w-full max-w-2xl bg-card border border-border rounded-lg shadow-lg p-8 text-center">
        {icon_html}
        <div class="text-6xl font-bold text-muted-foreground mb-2">{status_code}</div>
        <h1 class="text-2xl font-bold text-foreground mb-2">{escape(title)}</h1>
        <p class="text-sm text-muted-foreground">{escape(message)}</p>
        {details_html}
        <a href="{escape(action_url)}"
           class="inline-block px-6 py-3 rounded-md bg-primary text-primary-foreground font-medium mt-4 hover:bg-primary/90 transition-colors">{escape(action_text)}</a>
    </div>
    """

    layout = StandaloneLayout(config=config, context=context)
    return layout.render(content)
