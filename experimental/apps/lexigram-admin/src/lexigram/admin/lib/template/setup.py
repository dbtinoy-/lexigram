"""Template utilities for lexigram-admin.

Provides simple template rendering functions for standalone pages
like login, error, etc. Uses StandaloneLayout for consistent styling.
"""

from typing import Any

from lexigram.admin.lib.template.layout import (
    _auth_form,
    _primary_link,
    _standalone_card,
)
from lexigram.ui import EmailInput, PasswordInput, TextInput, el


def render_setup_page(
    error: str = "",
    site_name: str = "Lexigram Admin",
    locked: bool = False,
    csrf_token: str = "",
    setup_token_required: bool = False,
    login_url: str = "/admin/login",
    setup_url: str = "/admin/setup",
    base_url: str = "/admin",
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
        login_url: Mounted route used by the locked-state login link.
        setup_url: Mounted form action for the setup route.
        base_url: Mounted admin base URL used for shared assets.

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
            _primary_link("Go to Login", login_url),
            class_="text-center",
        )
        return _standalone_card(
            "Setup Complete",
            "Setup Complete",
            "An administrator account already exists. Please log in with your credentials.",
            [action],
            site_name=site_name,
            base_url=base_url,
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
        setup_url,
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
        base_url=base_url,
        flash_messages=flash_messages,
    )
