"""Framework integration (DI wiring) for the feature-flag subsystem.

Exports:
    FeatureFlagsProvider: Provider that registers flag infrastructure in the container.
"""

from __future__ import annotations

from lexigram.features.di.provider import FeatureFlagsProvider

__all__ = ["FeatureFlagsProvider"]
