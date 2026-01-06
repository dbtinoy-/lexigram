"""Tests for governance exceptions."""

from __future__ import annotations

import pytest

from lexigram.ai.governance import exceptions
from lexigram.contracts.ai.governance import GovernanceError as BaseGovernanceError


class TestGovernanceError:
    """Tests for the base GovernanceError exception."""

    def test_inherits_from_base(self) -> None:
        """Verify GovernanceError inherits from BaseGovernanceError."""
        assert issubclass(exceptions.GovernanceError, BaseGovernanceError)

    def test_can_raise_and_catch(self) -> None:
        """Verify GovernanceError can be raised and caught."""
        with pytest.raises(exceptions.GovernanceError):
            raise exceptions.GovernanceError("test error")

    def test_has_message(self) -> None:
        """Verify GovernanceError includes message."""
        msg = "test governance error"
        error = exceptions.GovernanceError(msg)
        assert msg in str(error)


class TestBudgetExceededError:
    """Tests for BudgetExceededError exception."""

    def test_inherits_from_governance_error(self) -> None:
        """Verify BudgetExceededError inherits from GovernanceError."""
        assert issubclass(exceptions.BudgetExceededError, exceptions.GovernanceError)

    def test_can_raise_and_catch(self) -> None:
        """Verify BudgetExceededError can be raised and caught."""
        with pytest.raises(exceptions.BudgetExceededError):
            raise exceptions.BudgetExceededError("Budget exceeded")

    def test_can_catch_as_governance_error(self) -> None:
        """Verify BudgetExceededError can be caught as GovernanceError."""
        with pytest.raises(exceptions.GovernanceError):
            raise exceptions.BudgetExceededError("Budget exceeded")

    def test_has_message(self) -> None:
        """Verify BudgetExceededError accepts a message."""
        error = exceptions.BudgetExceededError("budget exceeded")
        assert "budget exceeded" in str(error)


class TestRateLimitExceededError:
    """Tests for RateLimitExceededError exception."""

    def test_inherits_from_governance_error(self) -> None:
        """Verify RateLimitExceededError inherits from GovernanceError."""
        assert issubclass(exceptions.RateLimitExceededError, exceptions.GovernanceError)

    def test_stores_limit(self) -> None:
        """Verify stores limit attribute."""
        error = exceptions.RateLimitExceededError(
            limit=100,
            current=150,
            limit_type="rpm",
        )
        assert error.limit == 100

    def test_stores_current(self) -> None:
        """Verify stores current attribute."""
        error = exceptions.RateLimitExceededError(
            limit=100,
            current=150,
            limit_type="rpm",
        )
        assert error.current == 150

    def test_stores_limit_type(self) -> None:
        """Verify stores limit_type attribute."""
        error = exceptions.RateLimitExceededError(
            limit=100,
            current=150,
            limit_type="tpm",
        )
        assert error.limit_type == "tpm"

    def test_limit_type_default_rpm(self) -> None:
        """Verify limit_type defaults to 'rpm'."""
        error = exceptions.RateLimitExceededError(
            limit=60,
            current=100,
        )
        assert error.limit_type == "rpm"

    def test_stores_user_id(self) -> None:
        """Verify stores optional user_id attribute."""
        error = exceptions.RateLimitExceededError(
            limit=100,
            current=150,
            user_id="user-789",
        )
        assert error.user_id == "user-789"

    def test_user_id_default_none(self) -> None:
        """Verify user_id defaults to None."""
        error = exceptions.RateLimitExceededError(
            limit=100,
            current=150,
        )
        assert error.user_id is None

    def test_message_format_rpm(self) -> None:
        """Verify error message format for RPM."""
        error = exceptions.RateLimitExceededError(
            limit=60,
            current=100,
            limit_type="rpm",
        )
        message = str(error)
        assert "RPM" in message
        assert "100" in message
        assert "60" in message

    def test_message_format_tpm(self) -> None:
        """Verify error message format for TPM."""
        error = exceptions.RateLimitExceededError(
            limit=100000,
            current=150000,
            limit_type="tpm",
        )
        message = str(error)
        assert "TPM" in message

    def test_can_raise_and_catch(self) -> None:
        """Verify RateLimitExceededError can be raised and caught."""
        with pytest.raises(exceptions.RateLimitExceededError):
            raise exceptions.RateLimitExceededError(
                limit=60,
                current=100,
            )


class TestModelAccessDeniedError:
    """Tests for ModelAccessDeniedError exception."""

    def test_inherits_from_governance_error(self) -> None:
        """Verify ModelAccessDeniedError inherits from GovernanceError."""
        assert issubclass(exceptions.ModelAccessDeniedError, exceptions.GovernanceError)

    def test_stores_model(self) -> None:
        """Verify stores model attribute."""
        error = exceptions.ModelAccessDeniedError(
            model="gpt-5",
            reason="restricted",
        )
        assert error.model == "gpt-5"

    def test_stores_reason(self) -> None:
        """Verify stores reason attribute."""
        error = exceptions.ModelAccessDeniedError(
            model="gpt-5",
            reason="in_denylist",
        )
        assert error.reason == "in_denylist"

    def test_valid_reason_values(self) -> None:
        """Verify accepts all valid reason values."""
        valid_reasons = ["restricted", "not_in_allowlist", "in_denylist"]
        for reason in valid_reasons:
            error = exceptions.ModelAccessDeniedError(
                model="gpt-5",
                reason=reason,
            )
            assert error.reason == reason

    def test_stores_user_id(self) -> None:
        """Verify stores optional user_id attribute."""
        error = exceptions.ModelAccessDeniedError(
            model="gpt-5",
            reason="restricted",
            user_id="user-abc",
        )
        assert error.user_id == "user-abc"

    def test_user_id_default_none(self) -> None:
        """Verify user_id defaults to None."""
        error = exceptions.ModelAccessDeniedError(
            model="gpt-5",
            reason="restricted",
        )
        assert error.user_id is None

    def test_message_format(self) -> None:
        """Verify error message format."""
        error = exceptions.ModelAccessDeniedError(
            model="claude-3",
            reason="restricted",
        )
        message = str(error)
        assert "claude-3" in message
        assert "restricted" in message

    def test_message_includes_user_id(self) -> None:
        """Verify message includes user_id when provided."""
        error = exceptions.ModelAccessDeniedError(
            model="gpt-5",
            reason="not_in_allowlist",
            user_id="user-xyz",
        )
        assert "user-xyz" in str(error)

    def test_can_raise_and_catch(self) -> None:
        """Verify ModelAccessDeniedError can be raised and caught."""
        with pytest.raises(exceptions.ModelAccessDeniedError):
            raise exceptions.ModelAccessDeniedError(
                model="gpt-5",
                reason="restricted",
            )


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """Verify all exceptions inherit from BaseGovernanceError."""
        assert issubclass(exceptions.BudgetExceededError, BaseGovernanceError)
        assert issubclass(exceptions.RateLimitExceededError, BaseGovernanceError)
        assert issubclass(exceptions.ModelAccessDeniedError, BaseGovernanceError)

    def test_all_exceptions_inherit_from_governance_error(self) -> None:
        """Verify all leaf exceptions inherit from GovernanceError."""
        assert issubclass(exceptions.BudgetExceededError, exceptions.GovernanceError)
        assert issubclass(exceptions.RateLimitExceededError, exceptions.GovernanceError)
        assert issubclass(exceptions.ModelAccessDeniedError, exceptions.GovernanceError)


class TestAllExports:
    """Tests for __all__ exports."""

    def test_all_contains_budget_exceeded_error(self) -> None:
        """Verify BudgetExceededError is in __all__."""
        assert "BudgetExceededError" in exceptions.__all__

    def test_all_contains_governance_error(self) -> None:
        """Verify GovernanceError is in __all__."""
        assert "GovernanceError" in exceptions.__all__

    def test_all_contains_model_access_denied_error(self) -> None:
        """Verify ModelAccessDeniedError is in __all__."""
        assert "ModelAccessDeniedError" in exceptions.__all__

    def test_all_contains_rate_limit_exceeded_error(self) -> None:
        """Verify RateLimitExceededError is in __all__."""
        assert "RateLimitExceededError" in exceptions.__all__

    def test_all_exports_count(self) -> None:
        """Verify __all__ has expected number of exports."""
        assert len(exceptions.__all__) == 5