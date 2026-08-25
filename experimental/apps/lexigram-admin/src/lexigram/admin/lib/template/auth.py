"""Template utilities for lexigram-admin auth pages.

Facade module: page sections live in dedicated sibling builders —
:mod:`.auth_login` (login/registration), :mod:`.auth_password` (password
reset), :mod:`.auth_mfa` (second-factor challenge and 2FA setup), and
:mod:`.auth_email` (email verification) — re-exported here so the
package-level import path stays stable.
"""

from __future__ import annotations

from lexigram.admin.lib.template.auth_email import (
    render_email_verified_page as render_email_verified_page,
)
from lexigram.admin.lib.template.auth_email import (
    render_verify_email_page as render_verify_email_page,
)
from lexigram.admin.lib.template.auth_login import (
    render_login_page as render_login_page,
)
from lexigram.admin.lib.template.auth_login import (
    render_register_page as render_register_page,
)
from lexigram.admin.lib.template.auth_mfa import (
    render_mfa_challenge_page as render_mfa_challenge_page,
)
from lexigram.admin.lib.template.auth_mfa import (
    render_mfa_setup_page as render_mfa_setup_page,
)
from lexigram.admin.lib.template.auth_password import (
    render_password_reset_confirm_page as render_password_reset_confirm_page,
)
from lexigram.admin.lib.template.auth_password import (
    render_password_reset_request_page as render_password_reset_request_page,
)

__all__ = [
    "render_email_verified_page",
    "render_login_page",
    "render_mfa_challenge_page",
    "render_mfa_setup_page",
    "render_password_reset_confirm_page",
    "render_password_reset_request_page",
    "render_register_page",
    "render_verify_email_page",
]
