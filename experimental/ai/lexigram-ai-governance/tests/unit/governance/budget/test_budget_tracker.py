"""Tests for BudgetTracker — TPM + cost enforcement with sliding windows.

All tests use a BudgetTracker constructed with no EventBus so no async
event emission is exercised (that would require a live event bus mock).
"""

from __future__ import annotations

import pytest

from lexigram.ai.governance.budget.tracker import (
    BudgetApproval,
    BudgetExceeded,
    BudgetTracker,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tracker(
    tpm_limit: int | None = None,
    cost_limit: float | None = None,
    window_seconds: float = 60.0,
) -> BudgetTracker:
    return BudgetTracker(
        tpm_limit=tpm_limit,
        cost_limit_hourly=cost_limit,
        window_seconds=window_seconds,
    )


# ---------------------------------------------------------------------------
# TPM enforcement
# ---------------------------------------------------------------------------


class TestBudgetTrackerTpm:
    @pytest.mark.asyncio
    async def test_check_budget_allows_when_under_tpm_limit(self) -> None:
        tracker = _tracker(tpm_limit=10_000)
        result = await tracker.check_budget("gpt-4", estimated_tokens=5_000)
        assert result.is_ok()
        approval = result.unwrap()
        assert isinstance(approval, BudgetApproval)
        assert approval.remaining_tokens is not None
        assert approval.remaining_tokens == 10_000  # nothing recorded yet

    @pytest.mark.asyncio
    async def test_check_budget_denies_when_over_tpm_limit(self) -> None:
        tracker = _tracker(tpm_limit=1_000)
        # Record usage that fills the window
        await tracker.record_usage("gpt-4", tokens_used=900, cost=0.0)
        result = await tracker.check_budget("gpt-4", estimated_tokens=200)
        assert result.is_err()
        exceeded = result.unwrap_err()
        assert isinstance(exceeded, BudgetExceeded)
        assert exceeded.limit_type == "tpm"
        assert exceeded.model == "gpt-4"
        assert exceeded.limit == 1_000.0

    @pytest.mark.asyncio
    async def test_check_budget_allows_at_exact_tpm_limit(self) -> None:
        tracker = _tracker(tpm_limit=1_000)
        await tracker.record_usage("gpt-4", tokens_used=500, cost=0.0)
        # current=500, estimated=500 → 500+500 == 1000 == limit → NOT exceeded
        result = await tracker.check_budget("gpt-4", estimated_tokens=500)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_check_budget_returns_remaining_tokens(self) -> None:
        tracker = _tracker(tpm_limit=10_000)
        await tracker.record_usage("gpt-4", tokens_used=3_000, cost=0.0)
        result = await tracker.check_budget("gpt-4", estimated_tokens=1_000)
        assert result.is_ok()
        approval = result.unwrap()
        assert approval.remaining_tokens == 7_000

    @pytest.mark.asyncio
    async def test_no_tpm_limit_always_allows(self) -> None:
        tracker = _tracker(tpm_limit=None)
        result = await tracker.check_budget("gpt-4", estimated_tokens=999_999)
        assert result.is_ok()
        assert result.unwrap().remaining_tokens is None

    @pytest.mark.asyncio
    async def test_tpm_is_model_specific(self) -> None:
        tracker = _tracker(tpm_limit=1_000)
        await tracker.record_usage("gpt-4", tokens_used=900, cost=0.0)
        # Different model — its own counter, so should still be under limit
        result = await tracker.check_budget("claude-3", estimated_tokens=500)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_tpm_is_tenant_specific(self) -> None:
        tracker = _tracker(tpm_limit=1_000)
        await tracker.record_usage("gpt-4", tokens_used=900, cost=0.0, tenant_id="tenant-a")
        # Different tenant — its own counter
        result = await tracker.check_budget(
            "gpt-4", estimated_tokens=500, tenant_id="tenant-b"
        )
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_exceeded_err_contains_current_and_limit(self) -> None:
        tracker = _tracker(tpm_limit=500)
        await tracker.record_usage("gpt-4", tokens_used=400, cost=0.0)
        result = await tracker.check_budget("gpt-4", estimated_tokens=200)
        exceeded = result.unwrap_err()
        assert exceeded.current == 400.0
        assert exceeded.limit == 500.0

    @pytest.mark.asyncio
    async def test_exceeded_result_uses_err_type_not_exception(self) -> None:
        tracker = _tracker(tpm_limit=100)
        await tracker.record_usage("gpt-4", tokens_used=99, cost=0.0)
        # Should return Err, not raise an exception
        result = await tracker.check_budget("gpt-4", estimated_tokens=50)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), BudgetExceeded)


# ---------------------------------------------------------------------------
# Cost enforcement
# ---------------------------------------------------------------------------


class TestBudgetTrackerCost:
    @pytest.mark.asyncio
    async def test_check_budget_allows_when_under_cost_limit(self) -> None:
        tracker = _tracker(cost_limit=10.0)
        result = await tracker.check_budget(
            "gpt-4", estimated_tokens=0, estimated_cost=5.0
        )
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_check_budget_denies_when_over_cost_limit(self) -> None:
        tracker = _tracker(cost_limit=1.0)
        await tracker.record_usage("gpt-4", tokens_used=0, cost=0.90)
        result = await tracker.check_budget(
            "gpt-4", estimated_tokens=0, estimated_cost=0.20
        )
        assert result.is_err()
        exceeded = result.unwrap_err()
        assert exceeded.limit_type == "cost"
        assert exceeded.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_cost_not_enforced_when_estimated_cost_is_zero(self) -> None:
        tracker = _tracker(cost_limit=0.01)
        result = await tracker.check_budget(
            "gpt-4", estimated_tokens=0, estimated_cost=0.0
        )
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_no_cost_limit_always_allows(self) -> None:
        tracker = _tracker(cost_limit=None)
        result = await tracker.check_budget(
            "gpt-4", estimated_tokens=0, estimated_cost=9999.0
        )
        assert result.is_ok()
        assert result.unwrap().remaining_cost is None

    @pytest.mark.asyncio
    async def test_cost_and_tpm_combined_denies_on_first_violation(self) -> None:
        tracker = _tracker(tpm_limit=100, cost_limit=1.0)
        # Hit TPM limit first
        await tracker.record_usage("gpt-4", tokens_used=99, cost=0.0)
        result = await tracker.check_budget(
            "gpt-4", estimated_tokens=50, estimated_cost=0.01
        )
        assert result.is_err()
        assert result.unwrap_err().limit_type == "tpm"


# ---------------------------------------------------------------------------
# record_usage()
# ---------------------------------------------------------------------------


class TestBudgetTrackerRecordUsage:
    @pytest.mark.asyncio
    async def test_record_usage_accumulates_tokens_in_window(self) -> None:
        tracker = _tracker(tpm_limit=10_000)
        await tracker.record_usage("gpt-4", tokens_used=3_000, cost=0.0)
        await tracker.record_usage("gpt-4", tokens_used=2_000, cost=0.0)
        result = await tracker.check_budget("gpt-4", estimated_tokens=4_999)
        assert result.is_ok()  # 5000 + 4999 = 9999 ≤ 10000

    @pytest.mark.asyncio
    async def test_record_usage_accumulates_cost_in_window(self) -> None:
        tracker = _tracker(cost_limit=1.0)
        await tracker.record_usage("gpt-4", tokens_used=0, cost=0.30)
        await tracker.record_usage("gpt-4", tokens_used=0, cost=0.40)
        # Current cost = 0.70; estimated 0.31 → total 1.01 > 1.0
        result = await tracker.check_budget(
            "gpt-4", estimated_tokens=0, estimated_cost=0.31
        )
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_record_usage_accepts_tenant_id(self) -> None:
        tracker = _tracker(tpm_limit=1_000)
        await tracker.record_usage(
            "gpt-4", tokens_used=800, cost=0.0, tenant_id="tenant-x"
        )
        # Global counter (no tenant) should still be zero
        result = await tracker.check_budget("gpt-4", estimated_tokens=999)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_approval_remaining_tokens_decreases_after_record(self) -> None:
        tracker = _tracker(tpm_limit=10_000)
        await tracker.record_usage("gpt-4", tokens_used=6_000, cost=0.0)
        result = await tracker.check_budget("gpt-4", estimated_tokens=100)
        approval = result.unwrap()
        assert approval.remaining_tokens == 4_000
