"""Lexigram Serialization — JSON serialization and schema utilities.

Provides a standard JSON interface backed by orjson (when available)
with automatic fallback to the stdlib ``json`` module.  All serializer
implementations live in the ``backends`` subpackage; the registry
enables content-type-based negotiation.

The package is zero-infrastructure — no DI provider is needed for basic
use.  Call ``SerializationModule.configure()`` to wire the serializer
into the IoC container for injection.

Basic Usage::

    from lexigram.serialization import dumps, loads, SerializationModule

Module Structure:
    - backends: JSON serializer backends (``OrjsonSerializer``, ``StdlibSerializer``)
    - config: Configuration models (``SerializationConfig``)
    - di: Dependency injection provider (``SerializationProvider``)
    - domain: Domain serialization support
    - exceptions: Serialization exception hierarchy (``SerializationError``)
    - module: ``SerializationModule`` IoC registration
    - registry: Content-type-based serializer registry (``SerializerRegistry``)
    - schema: Schema utilities
    - types: Enums and type aliases (``JSONBackend``, ``JSONSerializable``)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.serialization.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.contracts.core.serialization import (
        JsonSerializerProtocol,
        SerializerProtocol,
    )
    from lexigram.serialization.backends.json import (
        JSON_BACKEND,
        JSONDecodeError,
        OrjsonSerializer,
        StdlibSerializer,
        dumps,
        dumps_str,
        loads,
        loads_str,
    )
    from lexigram.serialization.config import SerializationConfig
    from lexigram.serialization.di.provider import SerializationProvider
    from lexigram.serialization.exceptions import SerializationError
    from lexigram.serialization.module import SerializationModule
    from lexigram.serialization.registry.registry import SerializerRegistry
    from lexigram.serialization.types import JSONBackend, JSONSerializable

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # --- Module ---
    "SerializationModule": ("lexigram.serialization.module", "SerializationModule"),
    # --- Config ---
    "SerializationConfig": ("lexigram.serialization.config", "SerializationConfig"),
    # --- Exceptions ---
    "SerializationError": ("lexigram.serialization.exceptions", "SerializationError"),
    # --- JSON operations (from backends) ---
    "JSON_BACKEND": ("lexigram.serialization.backends.json", "JSON_BACKEND"),
    "JSONDecodeError": ("lexigram.serialization.backends.json", "JSONDecodeError"),
    "dumps": ("lexigram.serialization.backends.json", "dumps"),
    "dumps_str": ("lexigram.serialization.backends.json", "dumps_str"),
    "loads": ("lexigram.serialization.backends.json", "loads"),
    "loads_str": ("lexigram.serialization.backends.json", "loads_str"),
    # --- Serializer implementations ---
    "OrjsonSerializer": ("lexigram.serialization.backends.json", "OrjsonSerializer"),
    "StdlibSerializer": ("lexigram.serialization.backends.json", "StdlibSerializer"),
    # --- Registry ---
    "SerializerRegistry": (
        "lexigram.serialization.registry.registry",
        "SerializerRegistry",
    ),
    # --- Types ---
    "JSONBackend": ("lexigram.serialization.types", "JSONBackend"),
    "JSONSerializable": ("lexigram.serialization.types", "JSONSerializable"),
    # --- Protocols ---
    "JsonSerializerProtocol": (
        "lexigram.contracts.core.serialization",
        "JsonSerializerProtocol",
    ),
    "SerializerProtocol": (
        "lexigram.contracts.core.serialization",
        "SerializerProtocol",
    ),
    # --- Provider ---
    "SerializationProvider": (
        "lexigram.serialization.di.provider",
        "SerializationProvider",
    ),
}


def __getattr__(name: str) -> Any:
    """Lazy-load symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "JSON_BACKEND",
    "JSONBackend",
    "JSONDecodeError",
    "JSONSerializable",
    "JsonSerializerProtocol",
    "OrjsonSerializer",
    "SerializationConfig",
    "SerializationError",
    "SerializationModule",
    "SerializationProvider",
    "SerializerProtocol",
    "SerializerRegistry",
    "StdlibSerializer",
    "dumps",
    "dumps_str",
    "loads",
    "loads_str",
]
