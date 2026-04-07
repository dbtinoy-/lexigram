"""Admin-specific validation rules.

Extends the core ``Rule`` ABC with admin domain constraints for email
addresses, passwords, and usernames.
"""

from __future__ import annotations

import re
from typing import Any

from lexigram.contracts.exceptions.domain import FieldError
from lexigram.result import Err, Ok, Result
from lexigram.validation.rules import AbstractRule

_ADMIN_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,64}$")


class IsValidAdminEmail(AbstractRule):
    """Validate that a value is a properly formatted admin email address.

    Requires an ``@`` separator, a local part, and a domain with at least
    one dot and a two-or-more character TLD.
    """

    def __call__(self, value: Any, field_name: str) -> Result[Any, FieldError]:
        if value is not None and not _ADMIN_EMAIL_RE.match(str(value)):
            return Err(
                FieldError(
                    field=field_name,
                    message=f"{field_name} is not a valid email address",
                    code="invalid_admin_email",
                )
            )
        return Ok(value)


class StrongPassword(AbstractRule):
    """Validate that a password meets admin strength requirements.

    Rules:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (non-alphanumeric)
    """

    def __call__(self, value: Any, field_name: str) -> Result[Any, FieldError]:
        if value is None:
            return Ok(value)
        pwd = str(value)
        if len(pwd) < 8:
            return Err(
                FieldError(
                    field=field_name,
                    message=f"{field_name} must be at least 8 characters",
                    code="password_too_short",
                )
            )
        if not re.search(r"[A-Z]", pwd):
            return Err(
                FieldError(
                    field=field_name,
                    message=f"{field_name} must contain at least one uppercase letter",
                    code="password_no_uppercase",
                )
            )
        if not re.search(r"[a-z]", pwd):
            return Err(
                FieldError(
                    field=field_name,
                    message=f"{field_name} must contain at least one lowercase letter",
                    code="password_no_lowercase",
                )
            )
        if not re.search(r"\d", pwd):
            return Err(
                FieldError(
                    field=field_name,
                    message=f"{field_name} must contain at least one digit",
                    code="password_no_digit",
                )
            )
        if not re.search(r"[^a-zA-Z0-9]", pwd):
            return Err(
                FieldError(
                    field=field_name,
                    message=f"{field_name} must contain at least one special character",
                    code="password_no_special",
                )
            )
        return Ok(value)


class IsValidUsername(AbstractRule):
    """Validate that a value is an acceptable admin username.

    Accepts only alphanumeric characters and underscores, with a length
    between 3 and 64 characters (inclusive).
    """

    def __call__(self, value: Any, field_name: str) -> Result[Any, FieldError]:
        if value is not None and not _USERNAME_RE.match(str(value)):
            return Err(
                FieldError(
                    field=field_name,
                    message=(
                        f"{field_name} must be 3-64 alphanumeric characters "
                        "or underscores"
                    ),
                    code="invalid_username",
                )
            )
        return Ok(value)
