"""IoC module for the secrets/credential vault subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.di.module import DynamicModule

from lexigram.di.module import Module, module
from lexigram.secrets.config import SecretsConfig
from lexigram.secrets.di.provider import SecretsProvider


@module()
class SecretsModule(Module):
    """IoC module for the secrets/credential vault subsystem."""

    @classmethod
    def configure(
        cls,
        config: SecretsConfig | None = None,
    ) -> DynamicModule:
        from lexigram.di.module import DynamicModule

        provider = SecretsProvider(config=config)
        return DynamicModule(
            module=cls,
            providers=[provider],
            exports=[SecretsConfig],
        )

    @classmethod
    def stub(
        cls,
        config: SecretsConfig | None = None,
    ) -> DynamicModule:
        """Return a ``DynamicModule`` pre-configured for testing."""
        return cls.configure(config=config)
