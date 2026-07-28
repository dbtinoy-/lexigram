"""Governance error classes."""

from __future__ import annotations

from lexigram.contracts.exceptions import LexigramError


class GovernanceError(LexigramError):
    """Base class for governance-related errors."""

    _code = "LEX_ERR_GOV_001"


class BudgetExceededError(GovernanceError):
    """Error raised when budget is exceeded."""

    _code = "LEX_ERR_GOV_002"


class PolicyViolationError(GovernanceError):
    """Error raised when policy is violated."""

    _code = "LEX_ERR_GOV_003"


__all__ = [
    "BudgetExceededError",
    "GovernanceError",
    "PolicyViolationError",
]
