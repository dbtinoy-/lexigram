"""Login and registration page sections for lexigram-admin auth templates."""

from __future__ import annotations

from typing import Any

from lexigram.admin.lib.template.layout import (
    _auth_footer,
    _auth_form,
    _flash_messages,
    _standalone_card,
)
from lexigram.ui import (
    EmailInput,
    Link,
    PasswordInput,
    TextInput,
    el,
)


def render_login_page(
    next_url: str = "/admin/",
    error: str = "",
    site_name: str = "Lexigram Admin",
    csrf_token: str = "",
    notice: str = "",
    registration_enabled: bool = False,
    email_err: str = "",
    password_err: str = "",
    login_url: str = "/admin/login",
    password_reset_url: str = "/admin/password-reset",  # noqa: S107
    register_url: str = "/admin/register",
    base_url: str = "/admin",
) -> str:
    """Render a standalone login page.

    Args:
        next_url: URL to redirect to after login.
        error: Error message to display.
        site_name: Site name for branding.
        csrf_token: CSRF token to embed as a hidden form field.
        notice: Optional success notice to display (e.g. after a password reset).
        registration_enabled: When ``True`` a "Create account" link to
            ``/admin/register`` is shown next to the password-reset link.
        email_err: Optional per-field error under the email input.
        password_err: Optional per-field error under the password input.
        login_url: Mounted form action for the login route.
        password_reset_url: Mounted password reset route.
        register_url: Mounted registration route.
        base_url: Mounted admin base URL used for shared assets.

    Returns:
        HTML string for login page.
    """
    flash_messages = _flash_messages(error, notice)

    footer_links: list[Any] = [
        Link("Forgot password?", password_reset_url, variant="primary"),
    ]
    if registration_enabled:
        footer_links.append(el("span", "|", class_="mx-2 text-muted-foreground"))
        footer_links.append(Link("Create account", register_url, variant="primary"))

    form = _auth_form(
        login_url,
        csrf_token,
        [
            EmailInput(
                name="email",
                label="Email",
                placeholder="your@email.com",
                required=True,
                error=email_err or None,
            ),
            PasswordInput(
                name="password",
                label="Password",
                placeholder="Password",
                required=True,
                error=password_err or None,
            ),
        ],
        "Sign In",
        hidden=[("next", next_url)],
    )

    return _standalone_card(
        "Login",
        "Sign In",
        "Please sign in to continue",
        [form, _auth_footer(*footer_links)],
        site_name=site_name,
        base_url=base_url,
        flash_messages=flash_messages,
    )


def render_register_page(
    site_name: str = "Lexigram Admin",
    csrf_token: str = "",
    error: str = "",
    notice: str = "",
    name: str = "",
    email: str = "",
    name_err: str = "",
    email_err: str = "",
    password_err: str = "",
    confirmation_err: str = "",
    register_url: str = "/admin/register",
    login_url: str = "/admin/login",
    base_url: str = "/admin",
) -> str:
    """Render a standalone self-service registration page.

    Args:
        site_name: Site name for branding.
        csrf_token: CSRF token to embed as a hidden form field.
        error: Error message to display.
        notice: Optional success notice to display.
        name: Previously submitted display name (re-shown on error).
        email: Previously submitted email (re-shown on error).
        name_err: Optional per-field error under the name input.
        email_err: Optional per-field error under the email input.
        password_err: Optional per-field error under the password input.
        confirmation_err: Optional per-field error under the confirm input.
        register_url: Mounted form action for registration.
        login_url: Mounted route used by the sign-in link.
        base_url: Mounted admin base URL used for shared assets.

    Returns:
        HTML string for the registration page.
    """
    flash_messages = _flash_messages(error, notice)

    form = _auth_form(
        register_url,
        csrf_token,
        [
            TextInput(
                name="name",
                label="Name",
                value=name,
                placeholder="Your name",
                required=True,
                error=name_err or None,
            ),
            EmailInput(
                name="email",
                label="Email",
                value=email,
                placeholder="your@email.com",
                required=True,
                error=email_err or None,
            ),
            PasswordInput(
                name="password",
                label="Password",
                placeholder="Password",
                required=True,
                error=password_err or None,
            ),
            PasswordInput(
                name="password_confirmation",
                label="Confirm Password",
                placeholder="Confirm password",
                required=True,
                error=confirmation_err or None,
            ),
        ],
        "Create Account",
    )

    return _standalone_card(
        "Register",
        "Create Account",
        "Register to access the admin panel",
        [
            form,
            _auth_footer(
                "Already have an account? ",
                Link("Sign in", login_url, variant="primary"),
            ),
        ],
        site_name=site_name,
        base_url=base_url,
        flash_messages=flash_messages,
    )


__all__ = ["render_login_page", "render_register_page"]
