"""
Serialization module for Lexigram Cache.

This module provides various serialization implementations for cache backends,
allowing developers to choose the appropriate serialization strategy based on
their needs (interoperability vs. performance vs. compatibility).

The AsyncStringSerializerProtocol protocol is defined in lexigram.contracts.serialization
and implemented by cache-specific serializers in this module.
"""

from __future__ import annotations

from lexigram.cache.exceptions import CacheSerializationError
from lexigram.cache.serialization.compression import CompressingSerializer
from lexigram.cache.serialization.json import JSONSerializer
from lexigram.cache.serialization.msgpack import MsgPackSerializer
from lexigram.cache.serialization.type_registry import DEFAULT_REGISTRY, TypeRegistry
from lexigram.contracts.core.serialization import AsyncStringSerializerProtocol

__all__ = [
    "DEFAULT_REGISTRY",
    "AsyncStringSerializerProtocol",
    "CacheSerializationError",
    "CompressingSerializer",
    "JSONSerializer",
    "MsgPackSerializer",
    "TypeRegistry",
]
