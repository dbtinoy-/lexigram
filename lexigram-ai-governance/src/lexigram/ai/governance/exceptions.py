"""Exception hierarchy for AI Governance."""

from __future__ import annotations

from lexigram.contracts.ai.governance import (
    BudgetExceededError,
    GovernanceError,
    ResourceExhaustedError,
)


class RateLimitExceededError(GovernanceError):
    """Raised when RPM or TPM limits are exceeded.

    Attributes:
        limit: Configured limit value.
        current: Current counter value.
        limit_type: Type of limit exceeded (``"rpm"`` or ``"tpm"``).
    """

    _code: str = "LEX_ERR_GOV_006"

    def __init__(
        self,
        limit: int,
        current: int,
        limit_type: str = "rpm",
        user_id: str | None = None,
    ) -> None:
        self.limit = limit
        self.current = current
        self.limit_type = limit_type
        self.user_id = user_id
        super().__init__(
            f"{limit_type.upper()} exceeded: {current}/{limit} (user={user_id})"
        )


class ModelAccessDeniedError(GovernanceError):
    """Raised when a user is denied access to a model by policy.

    Attributes:
        model: Model identifier that was denied.
        reason: Why access was denied (``"restricted"``, ``"not_in_allowlist"``,
                ``"in_denylist"``).
    """

    _code: str = "LEX_ERR_GOV_007"

    def __init__(
        self,
        model: str,
        reason: str,
        user_id: str | None = None,
    ) -> None:
        self.model = model
        self.reason = reason
        self.user_id = user_id
        super().__init__(
            f"Model access denied: model={model}, reason={reason} (user={user_id})"
        )


__all__ = [
    "BudgetExceededError",
    "GovernanceError",
    "ModelAccessDeniedError",
    "RateLimitExceededError",
    "ResourceExhaustedError",
]
