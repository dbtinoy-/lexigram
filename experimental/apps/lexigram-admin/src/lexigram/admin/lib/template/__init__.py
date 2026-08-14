"""Template utilities for lexigram-admin.

Provides simple template rendering functions for standalone pages
like login, error, etc. Uses StandaloneLayout for consistent styling.
"""

from __future__ import annotations

from lexigram.admin.lib.template.auth import (
    render_email_verified_page,
    render_login_page,
    render_mfa_challenge_page,
    render_mfa_setup_page,
    render_password_reset_confirm_page,
    render_password_reset_request_page,
    render_register_page,
    render_verify_email_page,
)
from lexigram.admin.lib.template.error import render_error_page
from lexigram.admin.lib.template.profile import render_profile_page
from lexigram.admin.lib.template.render import render_template
from lexigram.admin.lib.template.setup import render_setup_page

__all__ = [
    "_auth_footer",
    "_auth_form",
    "_code_input",
    "_email_badge",
    "_flash",
    "_flash_messages",
    "_primary_link",
    "_standalone_card",
    "render_email_verified_page",
    "render_error_page",
    "render_login_page",
    "render_mfa_challenge_page",
    "render_mfa_setup_page",
    "render_password_reset_confirm_page",
    "render_password_reset_request_page",
    "render_profile_page",
    "render_register_page",
    "render_setup_page",
    "render_template",
    "render_verify_email_page",
]
