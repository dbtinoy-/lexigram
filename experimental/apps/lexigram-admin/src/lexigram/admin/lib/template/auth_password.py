"""Password reset request/confirm page sections for lexigram-admin auth templates."""

from __future__ import annotations

from lexigram.admin.lib.template.layout import (
    _auth_footer,
    _auth_form,
    _flash_messages,
    _standalone_card,
)
from lexigram.ui import EmailInput, Link, PasswordInput


def render_password_reset_request_page(
    site_name: str = "Lexigram Admin",
    csrf_token: str = "",
    error: str = "",
    sent: bool = False,
    request_url: str = "/admin/password-reset",
    login_url: str = "/admin/login",
    base_url: str = "/admin",
) -> str:
    """Render a standalone password reset request page.

    Args:
        site_name: Site name for branding.
        csrf_token: CSRF token to embed as a hidden form field.
        error: Error message to display.
        sent: When True, shows the generic "check your email" notice
            (anti-enumeration; identical for known and unknown emails).
        request_url: Mounted form action for reset requests.
        login_url: Mounted route used by the sign-in link.
        base_url: Mounted admin base URL used for shared assets.

    Returns:
        HTML string for the request page.
    """
    flash_messages = _flash_messages(error)
    if sent:
        flash_messages.append(
            (
                "success",
                "If an account exists for that email, a password reset link has been sent.",
            )
        )

    form = _auth_form(
        request_url,
        csrf_token,
        [
            EmailInput(
                name="email",
                label="Email",
                placeholder="your@email.com",
                required=True,
                autofocus=True,
            ),
        ],
        "Send Reset Link",
    )

    return _standalone_card(
        "Password Reset",
        "Forgot Password?",
        "Enter your email and we'll send you a reset link",
        [
            form,
            _auth_footer(Link("Back to sign in", login_url, variant="primary")),
        ],
        site_name=site_name,
        base_url=base_url,
        flash_messages=flash_messages,
    )


def render_password_reset_confirm_page(
    token: str,
    site_name: str = "Lexigram Admin",
    csrf_token: str = "",
    error: str = "",
    password_err: str = "",
    confirmation_err: str = "",
    confirm_url: str = "",
    login_url: str = "/admin/login",
    base_url: str = "/admin",
) -> str:
    """Render a standalone password reset confirm page.

    Args:
        token: Raw reset token from the emailed link.
        site_name: Site name for branding.
        csrf_token: CSRF token to embed as a hidden form field.
        error: Error message to display.
        password_err: Optional per-field error under the password input.
        confirmation_err: Optional per-field error under the confirm input.
        confirm_url: Mounted form action for the token.
        login_url: Mounted route used by the sign-in link.
        base_url: Mounted admin base URL used for shared assets.

    Returns:
        HTML string for the confirm page.
    """
    flash_messages = _flash_messages(error)
    confirm_url = confirm_url or f"/admin/password-reset/{token}"

    form = _auth_form(
        confirm_url,
        csrf_token,
        [
            PasswordInput(
                name="password",
                label="New Password",
                placeholder="New password",
                required=True,
                autofocus=True,
                error=password_err or None,
            ),
            PasswordInput(
                name="password_confirmation",
                label="Confirm Password",
                placeholder="Repeat password",
                required=True,
                error=confirmation_err or None,
            ),
        ],
        "Reset Password",
    )

    return _standalone_card(
        "Set New Password",
        "Set New Password",
        "Choose a strong new password",
        [
            form,
            _auth_footer(Link("Back to sign in", login_url, variant="primary")),
        ],
        site_name=site_name,
        base_url=base_url,
        flash_messages=flash_messages,
    )


__all__ = [
    "render_password_reset_confirm_page",
    "render_password_reset_request_page",
]
