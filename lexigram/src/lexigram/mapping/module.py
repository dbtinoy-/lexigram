"""Mapping module for dependency injection."""

from __future__ import annotations

from lexigram.di.module import Module, module
from lexigram.mapping.core.mapper import ObjectMapperImpl
from lexigram.mapping.di.provider import MappingProvider


@module(
    providers=[MappingProvider],
    exports=[ObjectMapperImpl],
)
class MappingModule(Module):
    """Object-to-object mapping registry and mapper.

    Static module — no factory required.  Registers a shared
    :class:`~lexigram.mapping.mapper.MappingRegistry` and
    :class:`~lexigram.mapping.mapper.ObjectMapperImpl` singleton.

    Usage::

        @module(imports=[MappingModule])
        class AppModule(Module):
            pass
    """


__all__ = ["MappingModule"]
