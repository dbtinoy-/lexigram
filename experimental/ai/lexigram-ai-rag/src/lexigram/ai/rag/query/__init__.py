from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.ai.rag.query.base import (
        TransformationConfig,
        TransformationStrategy,
        TransformedQuery,
    )
    from lexigram.ai.rag.query.pipeline import TransformationPipeline
    from lexigram.ai.rag.query.transformers import (
        CustomQueryTransformer,
        HyDEGenerator,
        MultiQueryGenerator,
        QueryExpander,
        QueryRewriter,
        create_transformer,
    )

_LAZY_IMPORTS = {
    "TransformationStrategy": ".base",
    "TransformedQuery": ".base",
    "QueryTransformer": ".base",
    "TransformationConfig": ".base",
    "QueryExpander": ".transformers",
    "MultiQueryGenerator": ".transformers",
    "HyDEGenerator": ".transformers",
    "QueryRewriter": ".transformers",
    "CustomQueryTransformer": ".transformers",
    "create_transformer": ".transformers",
    "TransformationPipeline": ".pipeline",
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
