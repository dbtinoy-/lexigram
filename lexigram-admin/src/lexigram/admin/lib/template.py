"""Template utilities for lexigram-admin.

Provides simple template rendering functions for standalone pages
like login, error, etc. Uses StandaloneLayout for consistent styling.
"""

from __future__ import annotations

from typing import Any

from markupsafe import escape

from lexigram.admin.ui.layouts import (
    StandaloneLayout,
    StandaloneLayoutConfig,
    StandaloneLayoutContext,
)


def render_login_page(
    next_url: str = "/admin/",
    error: str = "",
    site_name: str = "Lexigram Admin",
    csrf_token: str = "",
) -> str:
    """Render a standalone login page.

    Args:
        next_url: URL to redirect to after login.
        error: Error message to display.
        site_name: Site name for branding.
        csrf_token: CSRF token to embed as a hidden form field.

    Returns:
        HTML string for login page.
    """
    flash_messages: list[tuple[str, str]] = []
    if error:
        flash_messages.append(("error", error))

    config = StandaloneLayoutConfig(
        app_name=site_name,
        show_footer=True,
        centered=True,
    )
    context = StandaloneLayoutContext(
        page_title="Login",
        flash_messages=flash_messages,
    )

    content = f"""
    <div class="w-full max-w-md bg-card border border-border rounded-lg shadow-lg p-8">
        <div class="text-center mb-6">
            <h1 class="text-2xl font-bold text-foreground mb-2">Sign In</h1>
            <p class="text-sm text-muted-foreground">Please sign in to continue</p>
        </div>
        <form method="post" action="/admin/login">
            <input type="hidden" name="csrf_token" value="{escape(csrf_token)}">
            <input type="hidden" name="next" value="{escape(next_url)}">
            <div class="mb-4">
                <label for="email" class="block text-sm font-medium text-foreground mb-2">Email</label>
                <input type="email" id="email" name="email" placeholder="your@email.com" required
                       class="w-full px-3 py-2 rounded-md border border-input bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring">
            </div>
            <div class="mb-4">
                <label for="password" class="block text-sm font-medium text-foreground mb-2">Password</label>
                <input type="password" id="password" name="password" placeholder="Password" required
                       class="w-full px-3 py-2 rounded-md border border-input bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring">
            </div>
            <button type="submit"
                    class="w-full py-2.5 rounded-md bg-primary text-primary-foreground font-medium cursor-pointer hover:bg-primary/90 transition-colors focus:outline-none focus:ring-2 focus:ring-ring">Sign In</button>
        </form>
    </div>
    """

    layout = StandaloneLayout(config=config, context=context)
    return layout.render(content)


def render_setup_page(
    error: str = "",
    site_name: str = "Lexigram Admin",
    locked: bool = False,
    csrf_token: str = "",
) -> str:
    """Render the first-run admin setup page.

    Args:
        error: Optional error message to display.
        site_name: Site name for branding.
        locked: When True, shows a locked state (setup already complete).
        csrf_token: CSRF token to embed as a hidden form field (only used when not locked).

    Returns:
        HTML string for the setup page.
    """
    flash_messages: list[tuple[str, str]] = []
    if error:
        category = "warning" if locked else "error"
        flash_messages.append((category, error))

    config = StandaloneLayoutConfig(
        app_name=site_name,
        show_footer=True,
        centered=True,
    )
    context = StandaloneLayoutContext(
        page_title="Initial Setup" if not locked else "Setup Complete",
        flash_messages=flash_messages,
    )

    if locked:
        content = """
        <div class="w-full max-w-md bg-card border border-border rounded-lg shadow-lg p-8 text-center">
            <h1 class="text-2xl font-bold text-foreground mb-2">✅ Setup Complete</h1>
            <p class="text-sm text-muted-foreground mb-4">An administrator account already exists.<br>
            Please log in with your credentials.</p>
            <a href="/admin/login"
               class="block w-full py-2.5 rounded-md bg-primary text-primary-foreground font-medium text-center hover:bg-primary/90 transition-colors">Go to Login</a>
        </div>
        """
    else:
        content = f"""
        <div class="w-full max-w-md bg-card border border-border rounded-lg shadow-lg p-8">
            <div class="text-center mb-6">
                <h1 class="text-2xl font-bold text-foreground mb-2">Welcome to {escape(site_name)}</h1>
                <p class="text-sm text-muted-foreground">Create your administrator account to get started.</p>
            </div>
            <form method="post" action="/admin/setup">
                <input type="hidden" name="csrf_token" value="{escape(csrf_token)}">
                <div class="mb-4">
                    <label for="name" class="block text-sm font-medium text-foreground mb-2">Full Name</label>
                    <input type="text" id="name" name="name" placeholder="Your Name" required
                           class="w-full px-3 py-2 rounded-md border border-input bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring">
                </div>
                <div class="mb-4">
                    <label for="email" class="block text-sm font-medium text-foreground mb-2">Email Address</label>
                    <input type="email" id="email" name="email"
                           placeholder="admin@example.com" required
                           class="w-full px-3 py-2 rounded-md border border-input bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring">
                </div>
                <div class="mb-4">
                    <label for="password" class="block text-sm font-medium text-foreground mb-2">Password</label>
                    <input type="password" id="password" name="password"
                           placeholder="At least 8 characters" required minlength="8"
                           class="w-full px-3 py-2 rounded-md border border-input bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring">
                    <p class="text-xs text-muted-foreground mt-1">Minimum 8 characters.</p>
                </div>
                <div class="mb-4">
                    <label for="confirm_password" class="block text-sm font-medium text-foreground mb-2">Confirm Password</label>
                    <input type="password" id="confirm_password" name="confirm_password"
                           placeholder="Repeat password" required minlength="8"
                           class="w-full px-3 py-2 rounded-md border border-input bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring">
                </div>
                <button type="submit"
                        class="w-full py-2.5 rounded-md bg-primary text-primary-foreground font-medium cursor-pointer hover:bg-primary/90 transition-colors focus:outline-none focus:ring-2 focus:ring-ring">Create Account</button>
            </form>
        </div>
        """

    layout = StandaloneLayout(config=config, context=context)
    return layout.render(content)


def render_error_page(
    status_code: int = 500,
    title: str = "Error",
    message: str = "An error occurred",
    details: str = "",
    site_name: str = "Lexigram Admin",
    icon: str = "",
    action_text: str = "Return to Admin",
    action_url: str = "/admin/",
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
