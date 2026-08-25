"""Email verification landing/confirmed page sections for lexigram-admin templates."""

from __future__ import annotations

from lexigram.admin.lib.template.layout import (
    _auth_footer,
    _auth_form,
    _flash_messages,
    _primary_link,
    _standalone_card,
)
from lexigram.ui import Link, el


def render_verify_email_page(
    site_name: str = "Lexigram Admin",
    email: str = "",
    error: str = "",
    notice: str = "",
    csrf_token: str = "",
    next_url: str = "/admin/",
) -> str:
    """Render a standalone email verification landing page.

    Shown after a login attempt when the account email is unverified and
    enforcement is on.  Lets the user request a fresh verification link by
    posting to ``/admin/verify-email/resend``.

    Args:
        site_name: Site name for branding.
        email: Account email (displayed in the guidance copy).
        error: Error message to display.
        notice: Success notice to display (e.g. after a resend).
        csrf_token: CSRF token to embed as a hidden form field.
        next_url: Destination to redirect to after login.

    Returns:
        HTML string for the verification landing page.
    """
    flash_messages = _flash_messages(error, notice)
    copy = (
        "A verification link was sent"
        f"{(' to ' + email) if email else ''}. "
        "Click it to activate your account."
    )

    hint = el(
        "p",
        "If you don't see the email, check your spam folder or request a new link.",
        class_="text-sm text-muted-foreground mb-4",
    )
    form = _auth_form(
        "/admin/verify-email/resend",
        csrf_token,
        [],
        "Resend Verification Link",
        hidden=[("email", email), ("next", next_url)],
    )

    return _standalone_card(
        "Verify Your Email",
        "Verify Your Email",
        copy,
        [
            hint,
            form,
            _auth_footer(Link("Back to login", "/admin/login", variant="primary")),
        ],
        site_name=site_name,
        flash_messages=flash_messages,
    )


def render_email_verified_page(
    site_name: str = "Lexigram Admin",
    error: str = "",
    next_url: str = "/admin/",
) -> str:
    """Render a standalone "email verified" confirmation page.

    Shown after an admin clicks a valid verification link.  Serves as the
    post-verification entry point back into the login flow.

    Args:
        site_name: Site name for branding.
        error: Error message to display (e.g. expired or invalid token).
        next_url: Destination to redirect to after login.

    Returns:
        HTML string for the confirmation page.
    """
    flash_messages = _flash_messages(error)

    if error:
        heading = "Verification Failed"
        copy = error
        action_url = "/admin/login"
        action_label = "Back to login"
    else:
        heading = "Email Verified"
        copy = "Your email address has been verified — you can now sign in."
        action_url = f"/admin/login?next={next_url}"
        action_label = "Sign in"

    action = el(
        "div",
        _primary_link(action_label, action_url),
        class_="text-center",
    )

    return _standalone_card(
        "Email Verified",
        heading,
        copy,
        [action],
        site_name=site_name,
        flash_messages=flash_messages,
    )


__all__ = ["render_email_verified_page", "render_verify_email_page"]
