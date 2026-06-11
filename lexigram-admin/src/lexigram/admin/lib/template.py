"""Template utilities for lexigram-admin.

Provides simple template rendering functions for standalone pages
like login, error, etc. Uses StandaloneLayout for consistent styling.
"""

from __future__ import annotations

from typing import Any, cast

from markupsafe import escape

from lexigram.admin.ui.layouts import (
    StandaloneLayout,
    StandaloneLayoutConfig,
    StandaloneLayoutContext,
)
from lexigram.ui import (
    EmailInput,
    Link,
    PasswordInput,
    SubmitButton,
    TextInput,
    el,
    raw,
    render_to_string,
)


def _flash_messages(
    error: str,
    notice: str = "",
) -> list[tuple[str, str]]:
    """Build the standalone flash list from error/notice strings.

    Args:
        error: Error message to display.
        notice: Optional success notice to display.

    Returns:
        List of (category, message) tuples for the standalone layout.
    """
    messages: list[tuple[str, str]] = []
    if error:
        messages.append(("error", error))
    if notice:
        messages.append(("success", notice))
    return messages


def _standalone_card(
    page_title: str,
    heading: str,
    copy: str,
    children: list[Any],
    *,
    site_name: str = "Lexigram Admin",
    flash_messages: list[tuple[str, str]] | None = None,
) -> str:
    """Render a centred standalone auth card inside the standalone layout.

    Args:
        page_title: Document title used by the standalone layout.
        heading: Card heading text.
        copy: Subtitle text rendered under the heading.
        children: Body elements rendered inside the card.
        site_name: Site name for branding.
        flash_messages: Error/success flashes rendered above the card.

    Returns:
        Full standalone HTML document.
    """
    content = el(
        "div",
        el(
            "div",
            el("h1", heading, class_="text-2xl font-bold text-foreground mb-2"),
            el("p", copy, class_="text-sm text-muted-foreground"),
            class_="text-center mb-6",
        ),
        *children,
        class_="w-full max-w-md bg-card border border-border rounded-lg shadow-lg p-8",
    )
    layout = StandaloneLayout(
        config=StandaloneLayoutConfig(
            app_name=site_name,
            show_footer=True,
            centered=True,
        ),
        context=StandaloneLayoutContext(
            page_title=page_title,
            flash_messages=flash_messages or [],
        ),
    )
    return layout.render(render_to_string(content))


def _auth_form(
    action: str,
    csrf_token: str,
    fields: list[Any],
    submit_label: str,
    *,
    hidden: list[tuple[str, str]] | None = None,
    submit_variant: str = "default",
    footer: Any | None = None,
) -> Any:
    """Build a standard POST form with a CSRF field and submit button.

    Args:
        action: Form action URL.
        csrf_token: CSRF token embedded as a hidden field.
        fields: Input components rendered in vertical order.
        submit_label: Submit button text.
        hidden: Extra hidden (name, value) fields.
        submit_variant: Button variant (default or destructive).
        footer: Optional element rendered after the submit button.

    Returns:
        An ``el()`` form tree.
    """
    children: list[Any] = [
        el("input", type="hidden", name="csrf_token", value=csrf_token),
    ]
    children.extend(
        el("input", type="hidden", name=name, value=value)
        for name, value in (hidden or [])
    )
    children.extend(el("div", field, class_="mb-4") for field in fields)
    children.append(
        SubmitButton(
            label=submit_label, variant=cast("Any", submit_variant), class_="w-full"
        )
    )
    if footer is not None:
        children.append(footer)
    return el("form", *children, method="post", action=action)


def _code_input(label: str) -> Any:
    """Build the standard 6-digit one-time code input.

    Args:
        label: Field label text.

    Returns:
        An ``el()`` tree with the labelled code input.
    """
    return TextInput(
        name="code",
        label=label,
        inputmode="numeric",
        autocomplete="one-time-code",
        pattern="[0-9]{6}",
        maxlength=6,
        placeholder="123456",
        required=True,
        autofocus=True,
    )


def _email_badge(verified: bool) -> Any:
    """Render an email verification status strip.

    Args:
        verified: True when the email address is verified.

    Returns:
        An ``el()`` tree with the status text.
    """
    badge_text = "verified" if verified else "not verified"
    badge_class = "text-green-600" if verified else "text-foreground"
    return el(
        "div",
        el(
            "p",
            "Email address: ",
            el("span", badge_text, class_=f"font-medium {badge_class}"),
            class_="text-sm text-foreground",
        ),
        class_="mb-6 p-3 rounded-md bg-muted",
    )


def _primary_link(label: str, href: str, extra_class: str = "") -> Any:
    """Render a primary-button-styled anchor link.

    Args:
        label: Link text.
        href: Destination URL.
        extra_class: Additional CSS classes.

    Returns:
        An ``el()`` anchor tree.
    """
    return el(
        "a",
        label,
        href=href,
        class_=(
            "inline-flex items-center justify-center gap-2 whitespace-nowrap "
            "rounded-md text-sm font-medium ring-offset-background transition-colors "
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring "
            "focus-visible:ring-offset-2 bg-primary text-primary-foreground "
            f"hover:bg-primary/90 h-10 px-4 py-2 {extra_class}"
        ),
    )


def _auth_footer(*children: Any) -> Any:
    """Render a centred footer line under an auth form.

    Args:
        *children: Link/text elements to render.

    Returns:
        An ``el()`` paragraph tree.
    """
    return el("p", *children, class_="mt-4 text-center text-sm")


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


def render_setup_page(
    error: str = "",
    site_name: str = "Lexigram Admin",
    locked: bool = False,
    csrf_token: str = "",
    setup_token_required: bool = False,
) -> str:
    """Render the first-run admin setup page.

    Args:
        error: Optional error message to display.
        site_name: Site name for branding.
        locked: When True, shows a locked state (setup already complete).
        csrf_token: CSRF token to embed as a hidden form field (only used when not locked).
        setup_token_required: When True, an extra setup-token field is shown
            so an ``ADMIN_SETUP_TOKEN`` guard configured via the environment
            or admin config can be satisfied.

    Returns:
        HTML string for the setup page.
    """
    flash_messages: list[tuple[str, str]] = []
    if error:
        category = "warning" if locked else "error"
        flash_messages.append((category, error))

    if locked:
        action = el(
            "div",
            _primary_link("Go to Login", "/admin/login"),
            class_="text-center",
        )
        return _standalone_card(
            "Setup Complete",
            "Setup Complete",
            "An administrator account already exists. Please log in with your credentials.",
            [action],
            site_name=site_name,
            flash_messages=flash_messages,
        )

    fields: list[Any] = [
        TextInput(
            name="name",
            label="Full name",
            placeholder="Jane Doe",
            required=True,
            autofocus=True,
        ),
        EmailInput(
            name="email",
            label="Email",
            placeholder="your@email.com",
            required=True,
            autocomplete="email",
        ),
        PasswordInput(
            name="password",
            label="Password",
            placeholder="Password",
            required=True,
            autocomplete="new-password",
        ),
        PasswordInput(
            name="confirm_password",
            label="Confirm password",
            placeholder="Confirm password",
            required=True,
            autocomplete="new-password",
        ),
    ]
    if setup_token_required:
        fields.append(
            TextInput(
                name="setup_token",
                label="Setup token",
                placeholder="Setup token",
                required=True,
            ),
        )

    form = _auth_form(
        "/admin/setup",
        csrf_token,
        fields,
        "Create Administrator",
    )

    return _standalone_card(
        "Setup",
        "Create Administrator",
        "Set up the first administrative account for this application",
        [form],
        site_name=site_name,
        flash_messages=flash_messages,
    )


def render_profile_page(
    *,
    name: str,
    email: str,
    roles: list[str],
    user_id: str,
    mfa_enabled: bool,
    csrf_token: str,
    current_password_err: str = "",
    new_password_err: str = "",
    confirmation_err: str = "",
) -> str:
    """Render the user profile page content for the admin shell.

    Displays account details, two-factor authentication status, and a
    change-password form.  MFA management (setup/disable) lives on the
    dedicated ``/admin/profile/mfa`` screen; this page links to it.

    Args:
        name: Display name of the current user.
        email: Email of the current user.
        roles: Roles assigned to the current user.
        user_id: Identifier of the current user.
        mfa_enabled: Whether two-factor authentication is active.
        csrf_token: CSRF token for the change-password form.
        current_password_err: Optional per-field error under the current-password input.
        new_password_err: Optional per-field error under the new-password input.
        confirmation_err: Optional per-field error under the confirm input.

    Returns:
        HTML string fragment for the profile page body.
    """

    def field_error(message: str) -> str:
        return (
            f'<p class="mt-1 text-xs text-destructive" role="alert">{escape(message)}</p>'
            if message
            else ""
        )

    error_ring = "border-destructive focus:ring-destructive"
    current_classes = f"mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring {error_ring if current_password_err else ''}"
    new_classes = f"mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring {error_ring if new_password_err else ''}"
    confirm_classes = f"mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring {error_ring if confirmation_err else ''}"
    initials = "".join(part[0] for part in name.split()[:2]).upper() or "?"
    role_chips = "".join(
        f'<span class="inline-flex items-center rounded-full bg-accent px-2.5 py-0.5 text-xs font-medium text-accent-foreground">{escape(role)}</span>'
        for role in roles
    )
    mfa_badge = (
        '<span class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700">Enabled</span>'
        if mfa_enabled
        else '<span class="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">Disabled</span>'
    )
    return f"""
    <div class="max-w-3xl mx-auto space-y-6">
      <div class="rounded-lg border border-border bg-card shadow-sm">
        <div class="flex items-center gap-4 p-6">
          <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary text-lg font-bold text-primary-foreground">{escape(initials)}</div>
          <div class="min-w-0">
            <h2 class="text-xl font-bold text-foreground">{escape(name)}</h2>
            <p class="text-sm text-muted-foreground">{escape(email)}</p>
            <div class="mt-2 flex flex-wrap gap-1.5">{role_chips or '<span class="text-xs text-muted-foreground">No roles</span>'}</div>
          </div>
        </div>
        <div class="border-t border-border px-6 py-3 text-xs text-muted-foreground">User ID: <code>{escape(user_id)}</code></div>
      </div>

      <div class="rounded-lg border border-border bg-card shadow-sm">
        <div class="border-b border-border px-6 py-4">
          <h3 class="text-lg font-semibold text-foreground">Security</h3>
        </div>
        <div class="px-6 py-4 space-y-6">
          <div class="flex items-center justify-between gap-4">
            <div>
              <p class="font-medium text-foreground">Two-factor authentication</p>
              <p class="text-sm text-muted-foreground">Add an extra layer of security to your account.</p>
            </div>
            <div class="flex items-center gap-3">
              {mfa_badge}
              <a href="/admin/profile/mfa"
                 class="inline-flex items-center rounded-md border border-input bg-background px-3 py-1.5 text-sm font-medium text-foreground shadow-sm hover:bg-accent">Manage</a>
            </div>
          </div>
          <hr class="border-border" />
          <form method="post" action="/admin/profile/password" class="space-y-4">
            <input type="hidden" name="csrf_token" value="{escape(csrf_token)}" />
            <div>
              <label for="current_password" class="block text-sm font-medium text-foreground">Current password</label>
              <input type="password" name="current_password" id="current_password" required
                     class="{current_classes}" />
              {field_error(current_password_err)}
            </div>
            <div class="grid gap-4 sm:grid-cols-2">
              <div>
                <label for="new_password" class="block text-sm font-medium text-foreground">New password</label>
                <input type="password" name="new_password" id="new_password" required minlength="8"
                       class="{new_classes}" />
                {field_error(new_password_err)}
              </div>
              <div>
                <label for="new_password_confirmation" class="block text-sm font-medium text-foreground">Confirm new password</label>
                <input type="password" name="new_password_confirmation" id="new_password_confirmation" required minlength="8"
                       class="{confirm_classes}" />
                {field_error(confirmation_err)}
              </div>
            </div>
            <button type="submit"
                    class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90">Change password</button>
          </form>
        </div>
      </div>
    </div>
    """


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
