"""Tests for audit hooks."""

from __future__ import annotations

import pytest

from lexigram.audit.hooks import (
    AuditEntryCreatedHook,
    AuditPurgeScheduledHook,
    AuditVerificationScheduledHook,
)


class TestAuditEntryCreatedHook:
    """Tests for AuditEntryCreatedHook."""

    def test_hook_creation(self) -> None:
        hook = AuditEntryCreatedHook(
            action="user.login",
            actor_id="user-123",
            resource_type="User",
        )
        assert hook.action == "user.login"
        assert hook.actor_id == "user-123"
        assert hook.resource_type == "User"

    def test_hook_default_resource_type(self) -> None:
        hook = AuditEntryCreatedHook(
            action="system.start",
            actor_id="system",
        )
        assert hook.resource_type == ""

    def test_hook_is_frozen(self) -> None:
        hook = AuditEntryCreatedHook(
            action="test",
            actor_id="actor",
            resource_type="Resource",
        )
        with pytest.raises(AttributeError):
            hook.action = "modified"

    def test_hook_immutable(self) -> None:
        hook = AuditEntryCreatedHook(
            action="test",
            actor_id="actor",
        )
        assert hook.__dataclass_fields__


class TestAuditPurgeScheduledHook:
    """Tests for AuditPurgeScheduledHook."""

    def test_hook_creation(self) -> None:
        hook = AuditPurgeScheduledHook(policy_name="default")
        assert hook.policy_name == "default"

    def test_hook_is_frozen(self) -> None:
        hook = AuditPurgeScheduledHook(policy_name="test")
        with pytest.raises(AttributeError):
            hook.policy_name = "modified"


class TestAuditVerificationScheduledHook:
    """Tests for AuditVerificationScheduledHook."""

    def test_hook_creation(self) -> None:
        hook = AuditVerificationScheduledHook(batch_size=100)
        assert hook.batch_size == 100

    def test_hook_batch_size_zero(self) -> None:
        hook = AuditVerificationScheduledHook(batch_size=0)
        assert hook.batch_size == 0

    def test_hook_is_frozen(self) -> None:
        hook = AuditVerificationScheduledHook(batch_size=50)
        with pytest.raises(AttributeError):
            hook.batch_size = 100


class TestHookImports:
    """Tests for hook module exports."""

    def test_all_exports_present(self) -> None:
        from lexigram.audit import hooks
        assert hasattr(hooks, "AuditEntryCreatedHook")
        assert hasattr(hooks, "AuditPurgeScheduledHook")
        assert hasattr(hooks, "AuditVerificationScheduledHook")

    def test_all_in_dunder_all(self) -> None:
        from lexigram.audit import hooks
        expected = [
            "AuditEntryCreatedHook",
            "AuditPurgeScheduledHook",
            "AuditVerificationScheduledHook",
        ]
        assert hooks.__all__ == expected