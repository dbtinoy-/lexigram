"""Object mapping module for transforming between domain models and DTOs.

Exports:
    MappingRegistry: Registry that stores mapper functions keyed by (source, target) type pairs.
    ObjectMapperImpl: Mapper that resolves and invokes registered mapper functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.mapping.core.mapper import MappingRegistry, ObjectMapperImpl
    from lexigram.mapping.exceptions import (
        MappingError as MappingError,
    )
    from lexigram.mapping.exceptions import (
        MappingExecutionError as MappingExecutionError,
    )
    from lexigram.mapping.exceptions import (
        MappingNotFoundError as MappingNotFoundError,
    )
    from lexigram.mapping.protocols import (
        TypeConverterProtocol as TypeConverterProtocol,
    )
    from lexigram.mapping.types import MapperProtocol as MapperProtocol
    from lexigram.mapping.types import MappingFn as MappingFn

_LAZY_IMPORTS: dict[str, str] = {
    "MappingRegistry": "lexigram.mapping.core.mapper",
    "ObjectMapperImpl": "lexigram.mapping.core.mapper",
    # config
    "MappingConfig": "lexigram.mapping.config",
    # exceptions
    "MappingError": "lexigram.mapping.exceptions",
    "MappingExecutionError": "lexigram.mapping.exceptions",
    "MappingNotFoundError": "lexigram.mapping.exceptions",
    # protocols (now in types)
    "MapperProtocol": "lexigram.mapping.types",
    # types
    "MappingFn": "lexigram.mapping.types",
    # provider
    "MappingModule": "lexigram.mapping.module",
    "MappingProvider": "lexigram.mapping.di.provider",
    # Internal protocols
    "TypeConverterProtocol": "lexigram.mapping.protocols",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS.keys())
