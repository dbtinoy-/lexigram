"""Tests for PolicyBasedRetention."""

from __future__ import annotations

import pytest

from lexigram.audit.retention.policy import PolicyBasedRetention
from lexigram.contracts.audit import (
    AuditEntry,
    AuditEventSeverity,
    RetentionDecision,
    RetentionPolicy,
)


class TestPolicyBasedRetention:
    """Tests for PolicyBasedRetention."""

    def _policy(self, **kwargs: object) -> PolicyBasedRetention:
        policy = RetentionPolicy(name="test", **kwargs)  # type: ignore[arg-type]
        return PolicyBasedRetention(policy=policy)

    @pytest.mark.asyncio
    async def test_default_retention_days(self) -> None:
        retention = self._policy(default_retention_days=365)
        entry = AuditEntry(action="a", actor_id="u")
        expiry = await retention.get_expiry(entry)
        assert expiry is not None
        delta = expiry - entry.occurred_at
        assert abs(delta.days - 365) <= 1

    @pytest.mark.asyncio
    async def test_zero_retention_days_means_indefinite(self) -> None:
        retention = self._policy(default_retention_days=0)
        entry = AuditEntry(action="a", actor_id="u")
        expiry = await retention.get_expiry(entry)
        assert expiry is None

    @pytest.mark.asyncio
    async def test_severity_override(self) -> None:
        retention = self._policy(
            default_retention_days=365,
            severity_overrides={"critical": 2555},
        )
        critical_entry = AuditEntry(
            action="a", actor_id="u", severity=AuditEventSeverity.CRITICAL
        )
        expiry = await retention.get_expiry(critical_entry)
        assert expiry is not None
        assert abs((expiry - critical_entry.occurred_at).days - 2555) <= 1

    @pytest.mark.asyncio
    async def test_evaluate_returns_retain_until(self) -> None:
        retention = self._policy(default_retention_days=365)
        entry = AuditEntry(action="a", actor_id="u")
        decision = await retention.evaluate(entry)
        assert decision == RetentionDecision.RETAIN_UNTIL

    @pytest.mark.asyncio
    async def test_evaluate_returns_retain_for_zero_days(self) -> None:
        retention = self._policy(default_retention_days=0)
        entry = AuditEntry(action="a", actor_id="u")
        decision = await retention.evaluate(entry)
        assert decision == RetentionDecision.RETAIN
