"""PromptRegistry — named template lookup and registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.prompt.exceptions import PromptNotFoundError

if TYPE_CHECKING:
    from lexigram.ai.prompt.template.base import AbstractPromptTemplate


class PromptRegistry:
    """A thread-safe, in-memory registry that maps names to templates.

    Templates are registered once and can thereafter be retrieved by name.
    The registry supports optional *namespacing* via dotted names
    (e.g. ``"support.greeting"``).

    Example::

        registry = PromptRegistry()
        registry.register("hello", tmpl)
        retrieved = registry.get("hello")
    """

    def __init__(self) -> None:
        self._store: dict[str, AbstractPromptTemplate] = {}

    def register(
        self,
        name: str,
        template: AbstractPromptTemplate,
        *,
        overwrite: bool = False,
    ) -> None:
        """Register *template* under *name*.

        Args:
            name: Lookup key.
            template: Template instance to register.
            overwrite: Allow replacing an existing registration.  Defaults to
                       ``False`` to prevent accidental overwrites.

        Raises:
            ValueError: *name* already registered and *overwrite* is ``False``.
        """
        if name in self._store and not overwrite:
            raise ValueError(
                f"Template '{name}' is already registered. "
                "Pass overwrite=True to replace it."
            )
        self._store[name] = template

    def get(self, name: str) -> AbstractPromptTemplate:
        """Retrieve a template by *name*.

        Args:
            name: Lookup key.

        Returns:
            The registered template.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptNotFoundError`:
                No template is registered under *name*.
        """
        try:
            return self._store[name]
        except KeyError:
            raise PromptNotFoundError(
                f"No template registered under '{name}'. "
                f"Available: {sorted(self._store)!r}"
            ) from None

    def list_names(self) -> list[str]:
        """Return a sorted list of all registered template names."""
        return sorted(self._store)

    def unregister(self, name: str) -> None:
        """Remove template *name* from the registry.

        Args:
            name: Lookup key.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptNotFoundError`:
                *name* is not registered.
        """
        if name not in self._store:
            raise PromptNotFoundError(f"Cannot unregister unknown template '{name}'.")
        del self._store[name]

    def __contains__(self, name: str) -> bool:
        return name in self._store

    def __len__(self) -> int:
        return len(self._store)

    def __repr__(self) -> str:  # pragma: no cover
        return f"PromptRegistry(templates={sorted(self._store)!r})"


__all__ = ["PromptRegistry"]
