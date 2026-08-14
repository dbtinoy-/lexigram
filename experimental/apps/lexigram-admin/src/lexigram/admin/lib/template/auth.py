"""Template utilities for lexigram-admin.

Provides simple template rendering functions for standalone pages
like login, error, etc. Uses StandaloneLayout for consistent styling.
"""

from typing import Any

from lexigram.admin.lib.template.layout import (
    _auth_footer,
    _auth_form,
    _code_input,
    _email_badge,
    _flash_messages,
    _primary_link,
    _standalone_card,
)
from lexigram.ui import (
    EmailInput,
    Link,
    PasswordInput,
    TextInput,
    el,
    raw,
    render_to_string,
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

    Returns:
        HTML string for login page.
    """
    flash_messages = _flash_messages(error, notice)

    footer_links: list[Any] = [
        Link("Forgot password?", "/admin/password-reset", variant="primary"),
    ]
    if registration_enabled:
        footer_links.append(el("span", "|", class_="mx-2 text-muted-foreground"))
        footer_links.append(
            Link("Create account", "/admin/register", variant="primary")
        )

    form = _auth_form(
        "/admin/login",
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
        flash_messages=flash_messages,
    )


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
    flash_messages = _flash_messages(error)
    if sent:
        flash_messages.append(
            (
                "success",
                "If an account exists for that email, a password reset link has been sent.",
            )
        )

    form = _auth_form(
        "/admin/password-reset",
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
            _auth_footer(Link("Back to sign in", "/admin/login", variant="primary")),
        ],
        site_name=site_name,
        flash_messages=flash_messages,
    )


def render_password_reset_confirm_page(
    token: str,
    site_name: str = "Lexigram Admin",
    csrf_token: str = "",
    error: str = "",
    password_err: str = "",
    confirmation_err: str = "",
) -> str:
    """Render a standalone password reset confirm page.

    Args:
        token: Raw reset token from the emailed link.
        site_name: Site name for branding.
        csrf_token: CSRF token to embed as a hidden form field.
        error: Error message to display.
        password_err: Optional per-field error under the password input.
        confirmation_err: Optional per-field error under the confirm input.

    Returns:
        HTML string for the confirm page.
    """
    flash_messages = _flash_messages(error)

    form = _auth_form(
        f"/admin/password-reset/{token}",
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
            _auth_footer(Link("Back to sign in", "/admin/login", variant="primary")),
        ],
        site_name=site_name,
        flash_messages=flash_messages,
    )


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

    Returns:
        HTML string for the registration page.
    """
    flash_messages = _flash_messages(error, notice)

    form = _auth_form(
        "/admin/register",
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
                Link("Sign in", "/admin/login", variant="primary"),
            ),
        ],
        site_name=site_name,
        flash_messages=flash_messages,
    )
