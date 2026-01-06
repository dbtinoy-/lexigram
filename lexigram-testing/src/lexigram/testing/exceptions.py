"""Testing-specific exceptions."""

from __future__ import annotations

from lexigram.contracts.exceptions import LexigramError


class TestingError(LexigramError):
    """Base exception for lexigram-testing operations."""

    _code: str = "LEX_ERR_TEST_001"


class TokenBudgetExceededError(TestingError):
    """Raised when an AITestClient operation would exceed the configured token budget.

    Prevents runaway LLM API costs in test suites by enforcing a per-run cap.

    Args:
        tokens_used: Tokens already consumed in this run.
        token_budget: The configured maximum.
    """

    _code: str = "LEX_ERR_TEST_002"

    def __init__(self, tokens_used: int, token_budget: int) -> None:
        self.tokens_used = tokens_used
        self.token_budget = token_budget
        super().__init__(
            f"Test token budget exhausted: {tokens_used}/{token_budget} tokens used. "
            "Increase max_tokens_per_run or reduce test LLM calls.",
            hint="Set max_tokens_per_run=0 to disable budget enforcement.",
        )


__all__ = ["TestingError", "TokenBudgetExceededError"]
