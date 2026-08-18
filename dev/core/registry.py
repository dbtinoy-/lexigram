from __future__ import annotations

from typing import Generic, TypeVar

GeneratorT = TypeVar("GeneratorT")

class GeneratorRegistry(Generic[GeneratorT]):
    """Registry for named script generators."""

    def __init__(self) -> None:
        self._items: dict[str, GeneratorT] = {}

    def register(self, name: str, generator: GeneratorT) -> None:
        """Register a generator under a unique name."""

        if name in self._items:
            raise ValueError(f"duplicate generator: {name}")
        self._items[name] = generator

    def get(self, name: str) -> GeneratorT | None:
        """Return a generator by name if it exists."""

        return self._items.get(name)

    def names(self) -> tuple[str, ...]:
        """Return registered generator names in deterministic order."""

        return tuple(sorted(self._items))
