"""Built-in authentication controller for Lexigram Admin (package facade).

Implements login/logout, MFA challenge/setup, password reset, and
registration/email-verification endpoints with standalone UI (no admin
shell). Method implementations live in sibling mixin modules.
"""

from __future__ import annotations

from lexigram.admin.controllers.auth.core import (
    AuthCoreMixin,
    _humanize_error,
    logger,
)
from lexigram.admin.controllers.auth.login import AuthLoginMixin
from lexigram.admin.controllers.auth.mfa import AuthMfaMixin
from lexigram.admin.controllers.auth.password_reset import AuthPasswordResetMixin
from lexigram.admin.controllers.auth.registration import AuthRegistrationMixin
from lexigram.di.decorators import inject


@inject
class AuthController(
    AuthLoginMixin,
    AuthMfaMixin,
    AuthPasswordResetMixin,
    AuthRegistrationMixin,
    AuthCoreMixin,
):
    """Built-in authentication controller for Lexigram Admin."""

    prefix = ""
