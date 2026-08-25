"""MFA challenge and 2FA setup page sections for lexigram-admin auth templates."""

from __future__ import annotations

from typing import Any

from lexigram.admin.lib.template.layout import (
    _auth_form,
    _code_input,
    _email_badge,
    _flash_messages,
    _standalone_card,
)
from lexigram.ui import el, raw, render_to_string


def render_mfa_challenge_page(
    email: str = "",
    error: str = "",
    csrf_token: str = "",
    next_url: str = "/admin/",
    factor: str = "totp",
    resend_notice: str = "",
) -> str:
    """Render a standalone second-factor challenge page.

    Shown after password authentication when a challenge is required;
    completes the login by posting a verification code to
    ``/admin/login/2fa``.  The ``factor`` argument switches the guidance
    copy between the TOTP authenticator and email OTP, and adds a resend
    form (``/admin/login/2fa/resend``) for the email factor.

    Args:
        email: Account email (displayed in the guidance copy).
        error: Error message to display.
        csrf_token: CSRF token to embed as a hidden form field.
        next_url: Destination to redirect to after successful verification.
        factor: Second factor in use — ``"totp"`` (default) or ``"email"``.
        resend_notice: Success notice to display (e.g. after a resend).

    Returns:
        HTML string for the challenge page.
    """
    flash_messages = _flash_messages(error, resend_notice)

    if factor == "email":
        guidance = (
            f"Enter the 6-digit code we emailed{(' to ' + email) if email else ''}"
        )
        resend_block = el(
            "div",
            el(
                "p",
                "Didn't receive a code?",
                class_="text-sm text-muted-foreground mb-2",
            ),
            _auth_form(
                "/admin/login/2fa/resend",
                csrf_token,
                [],
                "Resend code",
                hidden=[("email", email), ("next", next_url)],
                submit_variant="link",
            ),
            class_="mt-4 pt-4 border-t border-border text-center",
        )
    else:
        guidance = (
            f"Enter the 6-digit code from your authenticator app"
            f"{(' for ' + email) if email else ''}"
        )
        resend_block = None

    children: list[Any] = [
        _auth_form(
            "/admin/login/2fa",
            csrf_token,
            [_code_input("Code")],
            "Verify & Sign In",
            hidden=[("next", next_url)],
        ),
    ]
    if resend_block is not None:
        children.append(resend_block)

    return _standalone_card(
        "Two-Factor Authentication",
        "Verification Code",
        guidance,
        children,
        flash_messages=flash_messages,
    )


def render_mfa_setup_page(
    enabled: bool,
    qr_svg: str = "",
    secret: str = "",
    csrf_token: str = "",
    email_verified: bool | None = None,
) -> str:
    """Render the profile 2FA setup fragment for the admin shell.

    When 2FA is disabled the page shows a QR code and secret plus a
    confirm form posting to ``/admin/profile/mfa/setup``.  When enabled it
    shows a disable form posting to ``/admin/profile/mfa/disable``.  Flash
    messages are supplied by the shell (via the request context), not
    embedded here.

    Args:
        enabled: True when 2FA is already active.
        qr_svg: Inline SVG QR code (trusted output of the MFA service).
        secret: Base32 TOTP secret to store in the authenticator.
        csrf_token: CSRF token to embed as a hidden form field.
        email_verified: Optional email verification status badge; when
            omitted no status is rendered.

    Returns:
        HTML fragment for the setup section inside the admin shell.
    """
    badge = _email_badge(email_verified) if email_verified is not None else None

    if enabled:
        children: list[Any] = [
            _auth_form(
                "/admin/profile/mfa/disable",
                csrf_token,
                [_code_input("Current Code")],
                "Disable 2FA",
                submit_variant="destructive",
            ),
        ]
        children = ([badge] if badge is not None else []) + children
        heading = "Two-Factor Authentication"
        copy = "Enabled — your account is protected by an authenticator app"
    else:
        qr = el("div", raw(qr_svg), class_="flex justify-center mb-4")
        secret_block = el(
            "div",
            el(
                "p",
                "If you cannot scan, enter this secret manually:",
                class_="text-sm text-muted-foreground mb-1 break-all",
            ),
            el(
                "p",
                secret,
                class_="text-center font-mono text-sm bg-muted rounded-md p-2 mb-4 break-all",
            ),
        )
        form = _auth_form(
            "/admin/profile/mfa/setup",
            csrf_token,
            [_code_input("Verification Code")],
            "Enable 2FA",
        )
        children = ([badge] if badge is not None else []) + [qr, secret_block, form]
        heading = "Enable 2FA"
        copy = "Scan the QR code with your authenticator app"

    card = el(
        "div",
        el(
            "div",
            el("h1", heading, class_="text-2xl font-bold text-foreground mb-2"),
            el("p", copy, class_="text-sm text-muted-foreground"),
            class_="text-center mb-6",
        ),
        *children,
        class_="w-full max-w-md mx-auto bg-card border border-border rounded-lg shadow-lg p-8",
    )
    return render_to_string(card)


__all__ = ["render_mfa_challenge_page", "render_mfa_setup_page"]
