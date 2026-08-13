"""Tests for retention policy edge cases and source overrides."""

from __future__ import annotations

import pytest

from lexigram.audit.retention.policy import PolicyBasedRetention
from lexigram.contracts.audit import (
    AuditEntry,
    AuditEventSeverity,
    RetentionDecision,
    RetentionPolicy,
)


class TestPolicyBasedRetentionEdgeCases:
    """Additional edge case tests for PolicyBasedRetention."""

    def _policy(self, **kwargs: object) -> PolicyBasedRetention:
        policy = RetentionPolicy(name="test", **kwargs)  # type: ignore[arg-type]
        return PolicyBasedRetention(policy=policy)

    @pytest.mark.asyncio
    async def test_source_override(self) -> None:
        retention = self._policy(
            default_retention_days=365,
            source_overrides={"audit_purger": 30},
        )
        entry = AuditEntry(
            action="a", actor_id="u", source="audit_purger"
        )
        expiry = await retention.get_expiry(entry)
        assert expiry is not None
        assert abs((expiry - entry.occurred_at).days - 30) <= 1

    @pytest.mark.asyncio
    async def test_severity_takes_precedence_over_source(self) -> None:
        retention = self._policy(
            default_retention_days=365,
            severity_overrides={"high": 100},
            source_overrides={"my_source": 30},
        )
        entry = AuditEntry(
            action="a",
            actor_id="u",
            source="my_source",
            severity=AuditEventSeverity.HIGH,
        )
        expiry = await retention.get_expiry(entry)
        assert expiry is not None
        # Severity should take precedence
        assert abs((expiry - entry.occurred_at).days - 100) <= 1

    @pytest.mark.asyncio
    async def test_fallback_to_default(self) -> None:
        retention = self._policy(
            default_retention_days=180,
            severity_overrides={"critical": 2555},
            source_overrides={"custom": 7},
        )
        # No overrides match, should use default
        entry = AuditEntry(action="a", actor_id="u", severity=AuditEventSeverity.LOW)
        expiry = await retention.get_expiry(entry)
        assert expiry is not None
        assert abs((expiry - entry.occurred_at).days - 180) <= 1

    @pytest.mark.asyncio
    async def test_all_severity_levels(self) -> None:
        for severity in AuditEventSeverity:
            retention = self._policy(
                default_retention_days=100,
                severity_overrides={severity.value: 50},
            )
            entry = AuditEntry(action="a", actor_id="u", severity=severity)
            expiry = await retention.get_expiry(entry)
            assert expiry is not None
            assert abs((expiry - entry.occurred_at).days - 50) <= 1

    @pytest.mark.asyncio
    async def test_evaluate_returns_retain_for_indefinite(self) -> None:
        retention = self._policy(default_retention_days=0)
        entry = AuditEntry(action="a", actor_id="u")
        decision = await retention.evaluate(entry)
        assert decision == RetentionDecision.RETAIN

    @pytest.mark.asyncio
    async def test_evaluate_with_severity_override(self) -> None:
        retention = self._policy(
            default_retention_days=365,
            severity_overrides={"critical": 0},  # 0 = indefinite
        )
        entry = AuditEntry(
            action="a", actor_id="u", severity=AuditEventSeverity.CRITICAL
        )
        decision = await retention.evaluate(entry)
        assert decision == RetentionDecision.RETAIN

    @pytest.mark.asyncio
    async def test_get_expiry_returns_none_for_indefinite(self) -> None:
        retention = self._policy(default_retention_days=0)
        entry = AuditEntry(action="a", actor_id="u")
        expiry = await retention.get_expiry(entry)
        assert expiry is None

    @pytest.mark.asyncio
    async def test_source_override_indefinite(self) -> None:
        retention = self._policy(
            default_retention_days=365,
            source_overrides={"important": 0},
        )
        entry = AuditEntry(action="a", actor_id="u", source="important")
        expiry = await retention.get_expiry(entry)
        assert expiry is None
        decision = await retention.evaluate(entry)
        assert decision == RetentionDecision.RETAIN