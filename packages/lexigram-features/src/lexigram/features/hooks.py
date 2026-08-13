"""Root hook payload surface for lexigram-features.

Defines canonical payload dataclasses for feature-flag lifecycle hook points.
Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "FeatureFlagEvaluatedHook",
    "FeatureFlagUpdatedHook",
]


@dataclass(frozen=True, kw_only=True)
class FeatureFlagEvaluatedHook:
    """Payload fired when a feature flag is evaluated for a given context.

    Attributes:
        flag_key: Unique key of the feature flag that was evaluated.
        enabled: Resolved boolean result of the evaluation.
    """

    flag_key: str
    enabled: bool


@dataclass(frozen=True, kw_only=True)
class FeatureFlagUpdatedHook:
    """Payload fired when a feature flag definition is created or updated.

    Attributes:
        flag_key: Unique key of the feature flag that changed.
    """

    flag_key: str
