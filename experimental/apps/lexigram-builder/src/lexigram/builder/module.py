"""BuilderModule — composition entry point for the builder application."""

from __future__ import annotations

from lexigram.builder.config import BuilderConfig
from lexigram.di.module import DynamicModule, Module
from lexigram.di.module import module as module_decorator


@module_decorator()
class BuilderModule(Module):
    """Wires the builder's provider and exports its controller surface."""

    @classmethod
    def configure(cls, config: BuilderConfig | None = None) -> DynamicModule:
        from lexigram.builder.controllers.builder_controller import BuilderController
        from lexigram.builder.di.provider import BuilderProvider

        return DynamicModule(
            module=cls,
            providers=[BuilderProvider(config=config)],
            exports=[BuilderController],
        )
