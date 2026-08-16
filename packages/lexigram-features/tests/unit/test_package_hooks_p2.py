"""P2 hook surface import verification for lexigram-features."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass

import pytest


def test_features_hooks_root_module_exists() -> None:
    import lexigram.features
    from lexigram.features.hooks import (
        FeatureFlagEvaluatedHook,
        FeatureFlagUpdatedHook,
    )

    assert FeatureFlagEvaluatedHook.__name__ == "FeatureFlagEvaluatedHook"
    assert FeatureFlagUpdatedHook.__name__ == "FeatureFlagUpdatedHook"
    assert lexigram.features.FeatureFlagEvaluatedHook is FeatureFlagEvaluatedHook
    assert lexigram.features.FeatureFlagUpdatedHook is FeatureFlagUpdatedHook


def test_features_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.features.hooks import FeatureFlagEvaluatedHook

    hook = FeatureFlagEvaluatedHook(flag_key="new_ui", enabled=True)

    assert is_dataclass(hook)

    with pytest.raises(TypeError):
        FeatureFlagEvaluatedHook("new_ui", True)  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        hook.enabled = False  # type: ignore[misc]
