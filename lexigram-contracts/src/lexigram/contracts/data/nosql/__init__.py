"""NoSQL data contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.data.nosql.nosql import (
        BulkWriteResult,
        CollectionProtocol,
        DocumentResult,
        DocumentStoreProtocol,
    )
    from lexigram.contracts.data.nosql.nosql_repository import (
        DocumentRepositoryProtocol,
    )

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "BulkWriteResult": (
        "lexigram.contracts.data.nosql.nosql",
        "BulkWriteResult",
    ),
    "CollectionProtocol": (
        "lexigram.contracts.data.nosql.nosql",
        "CollectionProtocol",
    ),
    "DocumentRepositoryProtocol": (
        "lexigram.contracts.data.nosql.nosql_repository",
        "DocumentRepositoryProtocol",
    ),
    "DocumentResult": (
        "lexigram.contracts.data.nosql.nosql",
        "DocumentResult",
    ),
    "DocumentStoreProtocol": (
        "lexigram.contracts.data.nosql.nosql",
        "DocumentStoreProtocol",
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
    """Enumerate available attributes for IDE support."""
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "BulkWriteResult",
    "CollectionProtocol",
    "DocumentRepositoryProtocol",
    "DocumentResult",
    "DocumentStoreProtocol",
]
