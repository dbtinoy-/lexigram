"""Lexigram AI — Unified AI/ML Layer.

Install `lexigram-ai` to get the full AI subsystem.
Import from sub-packages for granular control.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.ai.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.ai.config import AIConfig, ClientConfig, RAGConfig, VectorConfig
    from lexigram.ai.di.provider import AIProvider
    from lexigram.ai.module import AIModule

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "AIConfig": ("lexigram.ai.config", "AIConfig"),
    "AIModule": ("lexigram.ai.module", "AIModule"),
    "AIProvider": ("lexigram.ai.di.provider", "AIProvider"),
    "ClientConfig": ("lexigram.ai.config", "ClientConfig"),
    "RAGConfig": ("lexigram.ai.config", "RAGConfig"),
    "VectorConfig": ("lexigram.ai.config", "VectorConfig"),
}

__all__ = list(_LAZY_IMPORTS)


def __getattr__(name: str) -> object:
    """Lazy-load public symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr = _LAZY_IMPORTS[name]
        mod = importlib.import_module(module_path)
        value = getattr(mod, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Expose lazy-loaded names for tab completion and dir()."""
    return list(_LAZY_IMPORTS)
