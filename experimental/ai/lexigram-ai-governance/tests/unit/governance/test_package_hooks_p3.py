"""P3 hook surface import verification for lexigram-ai-governance."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest


def test_governance_hooks_root_module_exists() -> None:
    import lexigram.ai.governance
    from lexigram.ai.governance.hooks import (
        GovernanceAuditRecordedHook,
        GovernancePersistenceWrittenHook,
        GovernancePolicyEvaluatedHook,
    )

    assert lexigram.ai.governance.GovernanceAuditRecordedHook is GovernanceAuditRecordedHook
    assert (
        lexigram.ai.governance.GovernancePolicyEvaluatedHook
        is GovernancePolicyEvaluatedHook
    )
    assert (
        lexigram.ai.governance.GovernancePersistenceWrittenHook
        is GovernancePersistenceWrittenHook
    )
    assert "GovernanceAuditRecordedHook" in lexigram.ai.governance.__all__
    assert "GovernancePolicyEvaluatedHook" in lexigram.ai.governance.__all__
    assert "GovernancePersistenceWrittenHook" in lexigram.ai.governance.__all__


def test_governance_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.ai.governance.hooks import (
        GovernanceAuditRecordedHook,
        GovernancePersistenceWrittenHook,
        GovernancePolicyEvaluatedHook,
    )

    audited = GovernanceAuditRecordedHook(event_type="usage_logged")
    evaluated = GovernancePolicyEvaluatedHook(policy_name="budget_policy")
    persisted = GovernancePersistenceWrittenHook(backend="redis")

    assert is_dataclass(audited)
    assert is_dataclass(evaluated)
    assert is_dataclass(persisted)
    assert [field.name for field in fields(audited)] == ["event_type"]
    assert [field.name for field in fields(evaluated)] == ["policy_name"]
    assert [field.name for field in fields(persisted)] == ["backend"]

    with pytest.raises(TypeError):
        GovernanceAuditRecordedHook("usage_logged")  # type: ignore[misc]

    with pytest.raises(TypeError):
        GovernancePolicyEvaluatedHook("budget_policy")  # type: ignore[misc]

    with pytest.raises(TypeError):
        GovernancePersistenceWrittenHook("redis")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        audited.event_type = "other"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        evaluated.policy_name = "other_policy"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        persisted.backend = "memory"  # type: ignore[misc]
