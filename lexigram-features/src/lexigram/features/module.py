"""Feature flags module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.feature_flags import FlagProviderProtocol
from lexigram.di.module import DynamicModule, Module, module
from lexigram.features.di.provider import FeatureFlagsProvider


@module()
class FeatureFlagsModule(Module):
    """In-memory and extensible feature flag evaluation.

    Call :meth:`configure` to seed initial flag state from a
    :class:`~lexigram.features.config.FeatureFlagsConfig`.

    Usage::

        from lexigram.features.config import FeatureFlagsConfig

        @module(
            imports=[
                FeatureFlagsModule.configure(
                    FeatureFlagsConfig(initial_flags={"beta_feature": True})
                )
            ]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(cls, config: Any | None = None) -> DynamicModule:
        """Create a FeatureFlagsModule with explicit configuration.

        Args:
            config: :class:`~lexigram.features.config.FeatureFlagsConfig`
                or ``None`` for framework defaults (all flags disabled).

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.features.config import FeatureFlagsConfig

        if config is not None and not isinstance(config, FeatureFlagsConfig):
            raise TypeError(
                f"config must be FeatureFlagsConfig, got {type(config).__name__}"
            )

        return DynamicModule(
            module=cls,
            providers=[FeatureFlagsProvider(config=config)],
            exports=[FlagProviderProtocol],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return an in-memory FeatureFlagsModule for testing.

        Registers the feature flag provider with no flags enabled by
        default. Suitable for unit and integration tests.

        Returns:
            A DynamicModule with all flags disabled.
        """
        from lexigram.features.config import FeatureFlagsConfig

        return DynamicModule(
            module=cls,
            providers=[FeatureFlagsProvider(config=FeatureFlagsConfig())],
            exports=[FlagProviderProtocol],
        )


__all__ = ["FeatureFlagsModule"]
