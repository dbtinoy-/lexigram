"""Fail-closed behavior for governance persistence failures (audit §50).

Covers the config flag introduced by the fix and (Task 3) the manager-level
decision applied when the persistence backend is unavailable.
"""

from __future__ import annotations

from lexigram.ai.governance.config import GovernanceConfig


class TestGovernanceConfigPersistenceFailOpen:
    """The fail-open opt-in flag defaults to fail-closed."""

    def test_default_is_fail_closed(self) -> None:
        config = GovernanceConfig()
        assert config.fail_open_on_persistence_error is False

    def test_explicit_opt_in_overrides_default(self) -> None:
        config = GovernanceConfig(fail_open_on_persistence_error=True)
        assert config.fail_open_on_persistence_error is True
