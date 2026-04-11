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
        extra_head="""
        <style>
            .login-container {
                background: white;
                padding: 2rem;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 400px;
            }
            .dark .login-container {
                background: #1f2937;
            }
            .login-header {
                text-align: center;
                margin-bottom: 1.5rem;
            }
            .form-group {
                margin-bottom: 1rem;
            }
            .form-group label {
                display: block;
                margin-bottom: 0.5rem;
                font-weight: 500;
            }
            .form-group input {
                width: 100%;
                padding: 0.75rem;
                border: 1px solid #d1d5db;
                border-radius: 0.375rem;
            }
            .dark .form-group input {
                background: #374151;
                border-color: #4b5563;
                color: white;
            }
            .submit-btn {
                width: 100%;
                padding: 0.75rem;
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 0.375rem;
                font-weight: 500;
                cursor: pointer;
            }
            .submit-btn:hover {
                background: #2563eb;
            }
        </style>
        """,
    )

    content = f"""
    <div class="login-container">
        <div class="login-header">
            <h1>{escape(site_name)}</h1>
            <p>Please sign in to continue</p>
        </div>
        <form method="post" action="/admin/login">
            <input type="hidden" name="csrf_token" value="{escape(csrf_token)}">
            <input type="hidden" name="next" value="{escape(next_url)}">
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" placeholder="your@email.com" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" placeholder="Password" required>
            </div>
            <button type="submit" class="submit-btn">Sign In</button>
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
        extra_head="""
        <style>
            .setup-container {
                background: white;
                padding: 2rem;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 420px;
            }
            .dark .setup-container { background: #1f2937; }
            .setup-header { text-align: center; margin-bottom: 1.5rem; }
            .setup-header p { color: #6b7280; font-size: 0.9rem; }
            .form-group { margin-bottom: 1rem; }
            .form-group label {
                display: block; margin-bottom: 0.5rem; font-weight: 500;
            }
            .form-group input {
                width: 100%; padding: 0.75rem;
                border: 1px solid #d1d5db; border-radius: 0.375rem;
                box-sizing: border-box;
            }
            .dark .form-group input {
                background: #374151; border-color: #4b5563; color: white;
            }
            .submit-btn {
                width: 100%; padding: 0.75rem;
                background: #10b981; color: white; border: none;
                border-radius: 0.375rem; font-weight: 500; cursor: pointer;
                margin-top: 0.5rem;
            }
            .submit-btn:hover { background: #059669; }
            .login-btn {
                display: block; width: 100%; padding: 0.75rem;
                background: #3b82f6; color: white; border: none;
                border-radius: 0.375rem; font-weight: 500; cursor: pointer;
                text-align: center; text-decoration: none; margin-top: 0.5rem;
            }
            .login-btn:hover { background: #2563eb; }
            .hint { font-size: 0.8rem; color: #9ca3af; margin-top: 0.25rem; }
        </style>
        """,
    )

    if locked:
        content = """
        <div class="setup-container">
            <div class="setup-header">
                <h1>✅ Setup Complete</h1>
                <p>An administrator account already exists.<br>
                Please log in with your credentials.</p>
            </div>
            <a href="/admin/login" class="login-btn">Go to Login</a>
        </div>
        """
    else:
        content = f"""
        <div class="setup-container">
            <div class="setup-header">
                <h1>Welcome to {escape(site_name)}</h1>
                <p>Create your administrator account to get started.</p>
            </div>
            <form method="post" action="/admin/setup">
                <input type="hidden" name="csrf_token" value="{escape(csrf_token)}">
                <div class="form-group">
                    <label for="name">Full Name</label>
                    <input type="text" id="name" name="name" placeholder="Your Name" required>
                </div>
                <div class="form-group">
                    <label for="email">Email Address</label>
                    <input type="email" id="email" name="email"
                           placeholder="admin@example.com" required>
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password"
                           placeholder="At least 8 characters" required minlength="8">
                    <p class="hint">Minimum 8 characters.</p>
                </div>
                <div class="form-group">
                    <label for="confirm_password">Confirm Password</label>
                    <input type="password" id="confirm_password" name="confirm_password"
                           placeholder="Repeat password" required minlength="8">
                </div>
                <button type="submit" class="submit-btn">Create Account</button>
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
        extra_head="""
        <style>
            .error-container {
                background: white;
                padding: 2rem;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 600px;
                text-align: center;
            }
            .dark .error-container {
                background: #1f2937;
            }
            .error-code {
                font-size: 4rem;
                font-weight: bold;
                color: #9ca3af;
                margin-bottom: 0.5rem;
            }
            .error-btn {
                display: inline-block;
                padding: 0.75rem 1.5rem;
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 0.375rem;
                font-weight: 500;
                text-decoration: none;
                margin-top: 1rem;
            }
            .error-btn:hover {
                background: #2563eb;
            }
            .error-details {
                text-align: left;
                margin-top: 1rem;
            }
            .error-details pre {
                background: #f5f5f5;
                padding: 1rem;
                overflow-x: auto;
                border-radius: 0.375rem;
            }
            .dark .error-details pre {
                background: #374151;
            }
        </style>
        """,
    )

    details_html = ""
    if details:
        details_html = f"""
        <details class="error-details">
            <summary>Technical Details</summary>
            <pre>{escape(details)}</pre>
        </details>
        """

    icon_html = (
        f'<div style="font-size: 3rem; margin-bottom: 0.5rem;">{icon}</div>'
        if icon
        else ""
    )

    content = f"""
    <div class="error-container">
        {icon_html}
        <div class="error-code">{status_code}</div>
        <h1>{escape(title)}</h1>
        <p>{escape(message)}</p>
        {details_html}
        <a href="{escape(action_url)}" class="error-btn">{escape(action_text)}</a>
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
