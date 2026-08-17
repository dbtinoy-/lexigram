from __future__ import annotations

from collections.abc import Callable
from typing import Any

_PROMPT_REGISTRY: dict[str, dict[str, Any]] = {}


def prompt_template(
    name: str,
    version: str = "1.0",
    tags: list[str] | None = None,
) -> Callable[[type], type]:
    """Register a class as a named, versioned prompt template.

    Args:
        name: Unique template name used for retrieval from the registry.
        version: Semantic version string. Allows multiple versions to coexist.
        tags: Optional list of tags for filtering and discovery.

    Returns:
        Class decorator that registers the template in the prompt registry.

    Example::

        @prompt_template(name="rag.synthesis", version="2.0", tags=["rag"])
        class RAGSynthesisPrompt:
            system = "You are a helpful assistant."
            user = "Context:\\n{context}\\n\\nQuestion: {question}"
    """

    def decorator(cls: type) -> type:
        registry_key = f"{name}@{version}"
        if registry_key in _PROMPT_REGISTRY:
            existing = _PROMPT_REGISTRY[registry_key]["cls"].__name__
            raise ValueError(
                f"Prompt template {registry_key!r} already registered by {existing!r}"
            )
        cls._prompt_name = name  # type: ignore[attr-defined]
        cls._prompt_version = version  # type: ignore[attr-defined]
        cls._prompt_tags = tags or []  # type: ignore[attr-defined]
        _PROMPT_REGISTRY[registry_key] = {
            "cls": cls,
            "name": name,
            "version": version,
            "tags": tags or [],
        }
        return cls

    return decorator


__all__ = ["prompt_template"]
