"""Admin validator factory functions.

Provides pre-configured ``Validator`` instances for common admin user
operations such as creation and update.
"""

from __future__ import annotations

from lexigram.admin.validation.rules import (
    IsValidAdminEmail,
    IsValidUsername,
    StrongPassword,
)
from lexigram.validation.engine import ValidatorImpl as Validator
from lexigram.validation.rules import required


def create_user_validator() -> Validator:
    """Return a Validator configured for admin user creation.

    Applies:
    - ``email``: required + valid admin email format
    - ``password``: required + strong-password rules
    - ``username``: required + valid username format

    Returns:
        A fully configured :class:`~lexigram.validation.validator.Validator`.
    """
    return (
        Validator()
        .rule("email", required(), IsValidAdminEmail())
        .rule("password", required(), StrongPassword())
        .rule("username", required(), IsValidUsername())
    )


def update_user_validator() -> Validator:
    """Return a Validator configured for admin user updates.

    Applies email and username validation only; password is not required
    on updates (use a dedicated change-password flow instead).

    Applies:
    - ``email``: valid admin email format (optional field)
    - ``username``: valid username format (optional field)

    Returns:
        A fully configured :class:`~lexigram.validation.validator.Validator`.
    """
    return (
        Validator()
        .rule("email", IsValidAdminEmail())
        .rule("username", IsValidUsername())
    )
