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
    notice: str = "",
) -> str:
    """Render a standalone login page.

    Args:
        next_url: URL to redirect to after login.
        error: Error message to display.
        site_name: Site name for branding.
        csrf_token: CSRF token to embed as a hidden form field.
        notice: Optional success notice to display (e.g. after a password reset).

    Returns:
        HTML string for login page.
    """
    flash_messages: list[tuple[str, str]] = []
    if error:
        flash_messages.append(("error", error))
    if notice:
        flash_messages.append(("success", notice))

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


def render_password_reset_request_page(
    site_name: str = "Lexigram Admin",
    csrf_token: str = "",
    error: str = "",
    sent: bool = False,
) -> str:
    """Render a standalone password reset request page.

    Args:
        site_name: Site name for branding.
        csrf_token: CSRF token to embed as a hidden form field.
        error: Error message to display.
        sent: When True, shows the generic "check your email" notice
            (anti-enumeration; identical for known and unknown emails).

    Returns:
        HTML string for the request page.
    """
    flash_messages: list[tuple[str, str]] = []
    if error:
        flash_messages.append(("error", error))
    if sent:
        flash_messages.append(
            (
                "success",
                "If an account exists for that email, a password reset link has been sent.",
            )
        )

    config = StandaloneLayoutConfig(
        app_name=site_name,
        show_footer=True,
        centered=True,
    )
    context = StandaloneLayoutContext(
        page_title="Password Reset",
        flash_messages=flash_messages,
    )

    content = f"""
    <div class="w-full max-w-md bg-card border border-border rounded-lg shadow-lg p-8">
        <div class="text-center mb-6">
            <h1 class="text-2xl font-bold text-foreground mb-2">Forgot Password?</h1>
            <p class="text-sm text-muted-foreground">Enter your email and we'll send you a reset link</p>
        </div>
        <form method="post" action="/admin/password-reset">
            <input type="hidden" name="csrf_token" value="{escape(csrf_token)}">
            <div class="mb-4">
                <label for="email" class="block text-sm font-medium text-foreground mb-2">Email</label>
                <input type="email" id="email" name="email" placeholder="your@email.com" required autofocus
                       class="w-full px-3 py-2 rounded-md border border-input bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring">
            </div>
            <button type="submit"
                    class="w-full py-2.5 rounded-md bg-primary text-primary-foreground font-medium cursor-pointer hover:bg-primary/90 transition-colors focus:outline-none focus:ring-2 focus:ring-ring">Send Reset Link</button>
        </form>
        <p class="mt-4 text-center text-sm">
            <a href="/admin/login" class="text-primary hover:underline">Back to sign in</a>
        </p>
    </div>
    """

    layout = StandaloneLayout(config=config, context=context)
    return layout.render(content)


def render_password_reset_confirm_page(
    token: str,
    site_name: str = "Lexigram Admin",
    csrf_token: str = "",
    error: str = "",
) -> str:
    """Render a standalone password reset confirm page.

    Args:
        token: Raw reset token from the emailed link.
        site_name: Site name for branding.
        csrf_token: CSRF token to embed as a hidden form field.
        error: Error message to display.

    Returns:
        HTML string for the confirm page.
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
        page_title="Set New Password",
        flash_messages=flash_messages,
    )

    content = f"""
    <div class="w-full max-w-md bg-card border border-border rounded-lg shadow-lg p-8">
        <div class="text-center mb-6">
            <h1 class="text-2xl font-bold text-foreground mb-2">Set New Password</h1>
            <p class="text-sm text-muted-foreground">Choose a strong new password</p>
        </div>
        <form method="post" action="/admin/password-reset/{escape(token)}">
            <input type="hidden" name="csrf_token" value="{escape(csrf_token)}">
            <div class="mb-4">
                <label for="password" class="block text-sm font-medium text-foreground mb-2">New Password</label>
                <input type="password" id="password" name="password" placeholder="New password" required autofocus
                       class="w-full px-3 py-2 rounded-md border border-input bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring">
            </div>
            <div class="mb-4">
                <label for="password_confirmation" class="block text-sm font-medium text-foreground mb-2">Confirm Password</label>
                <input type="password" id="password_confirmation" name="password_confirmation" placeholder="Repeat password" required
                       class="w-full px-3 py-2 rounded-md border border-input bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring">
            </div>
            <button type="submit"
                    class="w-full py-2.5 rounded-md bg-primary text-primary-foreground font-medium cursor-pointer hover:bg-primary/90 transition-colors focus:outline-none focus:ring-2 focus:ring-ring">Reset Password</button>
        </form>
        <p class="mt-4 text-center text-sm">
            <a href="/admin/login" class="text-primary hover:underline">Back to sign in</a>
        </p>
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


def _page_shell(title: str, content: str) -> str:
    """Wrap standalone page content in the standard admin layout.

    Args:
        title: Page title for the layout header.
        content: Inner HTML body.

    Returns:
        Fully rendered HTML string.
    """
    config = StandaloneLayoutConfig(
        app_name="Lexigram Admin",
        show_footer=True,
        centered=True,
    )
    context = StandaloneLayoutContext(
        page_title=title,
        flash_messages=[],
    )
    layout = StandaloneLayout(config=config, context=context)
    return layout.render(content)


def _flash(error: str, notice: str) -> str:
    """Render inline error/notice flash messages.

    Args:
        error: Error message to display (empty hides the block).
        notice: Success notice to display (empty hides the block).

    Returns:
        HTML string with the flash blocks.
    """
    parts = []
    if error:
        parts.append(f'<div class="text-sm text-destructive">{escape(error)}</div>')
    if notice:
        parts.append(f'<div class="text-sm text-emerald-600">{escape(notice)}</div>')
    return "\n".join(parts)


def render_roles_list_page(
    roles: list[Any],
    *,
    error: str = "",
    notice: str = "",
    csrf_token: str = "",
) -> str:
    """Render the roles management list page.

    Args:
        roles: Roles to display.
        error: Optional error flash message.
        notice: Optional success flash message.
        csrf_token: CSRF token for the inline delete forms.

    Returns:
        HTML string for the roles list page.
    """
    rows = "\n".join(
        f"""
        <tr>
          <td>{escape(role.name)}</td>
          <td>{escape(role.description or "")}</td>
          <td>{len(role.permissions)}</td>
          <td>{"system" if role.is_system else "custom"}</td>
          <td>
            <a href="/admin/roles/{escape(role.name)}/edit">Edit</a>
            <form method="post" action="/admin/roles/{escape(role.name)}/delete" style="display:inline">
              <input type="hidden" name="csrf_token" value="{escape(csrf_token)}" />
              <button type="submit">Delete</button>
            </form>
          </td>
        </tr>
        """
        for role in roles
    )
    return _page_shell(
        "Roles",
        f"""
        <p><a href="/admin/roles/new">Create role</a></p>
        {_flash(error, notice)}
        <table>
          <thead><tr><th>Name</th><th>Description</th><th>Permissions</th><th>Type</th><th>Actions</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        """,
    )


def render_role_form_page(
    *,
    role: Any = None,
    permission_options: dict[str, list[str]] | None = None,
    selected: set[str] | None = None,
    error: str = "",
    notice: str = "",
    csrf_token: str = "",
) -> str:
    """Render the role create/edit form page.

    Args:
        role: Role being edited, or ``None`` for create.
        permission_options: Grouped permission inventory
            ``{resource: [perm, ...]}``.
        selected: Currently selected permission strings.
        error: Optional error flash message.
        notice: Optional success flash message.
        csrf_token: CSRF token for the form.

    Returns:
        HTML string for the role form page.
    """
    selected = selected or set()
    options = permission_options or {}
    groups = "\n".join(
        f"""
        <fieldset>
          <legend>{escape(resource)}</legend>
          {
            "".join(
                f'<label><input type="checkbox" name="permissions" value="{escape(perm)}" '
                f"{'checked' if perm in selected else ''}/> {escape(perm)}</label><br/>"
                for perm in perms
            )
        }
        </fieldset>
        """
        for resource, perms in options.items()
    )
    # Preserve permissions that exist on the role but are not part of the
    # built-in inventory (e.g. wildcards like "*" or app-defined strings):
    # hidden inputs carry them through the form untouched.
    all_options = {p for perms in options.values() for p in perms}
    preserved = "\n".join(
        f'<input type="hidden" name="permissions" value="{escape(perm)}" />'
        for perm in sorted(selected - all_options)
    )
    name_value = f'value="{escape(role.name)}"' if role else ""
    name_disabled = 'disabled="disabled"' if role and role.is_system else ""
    action = f"/admin/roles/{escape(role.name)}/edit" if role else "/admin/roles/new"
    return _page_shell(
        f"{'Edit' if role else 'Create'} role",
        f"""
        <form method="post" action="{action}">
          <input type="hidden" name="csrf_token" value="{escape(csrf_token)}" />
          {preserved}
          <label>Name
            <input type="text" name="name" {name_value} {name_disabled} required />
          </label>
          <label>Description
            <input type="text" name="description" value="{escape(role.description) if role else ""}" />
          </label>
          {groups}
          <input type="hidden" name="name" value="{escape(role.name) if role else ""}" />
          <button type="submit">Save</button>
        </form>
        {_flash(error, notice)}
        """,
    )


def render_users_list_page(
    users: list[Any],
    *,
    error: str = "",
    notice: str = "",
) -> str:
    """Render the admin users list page with role badges.

    Args:
        users: Admin user records to display.
        error: Optional error flash message.
        notice: Optional success flash message.

    Returns:
        HTML string for the users list page.
    """
    rows = "\n".join(
        f"""
        <tr>
          <td>{escape(getattr(user, "name", "") or "")}</td>
          <td>{escape(getattr(user, "email", "") or "")}</td>
          <td>
            {", ".join(escape(str(r)) for r in (getattr(user, "roles", None) or []))}
          </td>
          <td>
            <a href="/admin/users/{escape(str(getattr(user, "user_id", "")))}/roles">Edit roles</a>
          </td>
        </tr>
        """
        for user in users
    )
    return _page_shell(
        "Users",
        f"""
        {_flash(error, notice)}
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Roles</th><th>Actions</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        """,
    )


def render_user_roles_page(
    user: Any,
    roles: list[Any],
    *,
    role_names: set[str] | None = None,
    error: str = "",
    notice: str = "",
    csrf_token: str = "",
) -> str:
    """Render the user role assignment form.

    Args:
        user: The admin user being edited (or ``None`` when unknown).
        roles: Available roles to offer as checkboxes.
        role_names: Role names currently assigned to the user.
        error: Optional error flash message.
        notice: Optional success flash message.
        csrf_token: CSRF token for the form.

    Returns:
        HTML string for the user roles page.
    """
    role_names = role_names or set()
    checkboxes = "\n".join(
        f'<label><input type="checkbox" name="roles" value="{escape(r.name)}" '
        f"{'checked' if r.name in role_names else ''}/> {escape(r.name)}</label><br/>"
        for r in roles
    )
    user_label = escape(
        f"{getattr(user, 'name', '')} <{getattr(user, 'email', '')}>"
        if user
        else "unknown user"
    )
    return _page_shell(
        "User roles",
        f"""
        <form method="post" action="/admin/users/{escape(str(getattr(user, "user_id", "")))}/roles">
          <input type="hidden" name="csrf_token" value="{escape(csrf_token)}" />
          <p>{user_label}</p>
          {checkboxes}
          <button type="submit">Save</button>
        </form>
        {_flash(error, notice)}
        """,
    )
