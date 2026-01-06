from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.ai.rag.cache.base import CacheType, RAGCacheConfig
    from lexigram.ai.rag.cache.keys import CacheKeyBuilder
    from lexigram.ai.rag.cache.manager import RAGCache
    from lexigram.ai.rag.cache.stats import RAGCacheStats

_LAZY_IMPORTS = {
    "CacheType": "lexigram.ai.rag.cache.base",
    "RAGCacheConfig": "lexigram.ai.rag.cache.base",
    "CacheKeyBuilder": "lexigram.ai.rag.cache.keys",
    "RAGCacheStats": "lexigram.ai.rag.cache.stats",
    "RAGCache": "lexigram.ai.rag.cache.manager",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module_path = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path, __package__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__} has no attribute {name}")


def __dir__() -> list[str]:
    return list(_LAZY_IMPORTS.keys())


__all__ = list(_LAZY_IMPORTS.keys())
