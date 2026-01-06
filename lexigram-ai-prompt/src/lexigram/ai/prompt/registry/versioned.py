"""VersionedPromptStore — version history and rollback for named templates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lexigram.ai.prompt.exceptions import PromptNotFoundError, PromptVersionError

if TYPE_CHECKING:
    from lexigram.ai.prompt.template.base import AbstractPromptTemplate


@dataclass
class _VersionEntry:
    version: int
    template: AbstractPromptTemplate
    metadata: dict[str, Any] = field(default_factory=dict)


class VersionedPromptStore:
    """A store that maintains a full version history for each named template.

    Templates are added with :meth:`push`, which appends a new version and
    makes it the *current* (latest) version.  Previous versions remain
    accessible via :meth:`get_version` and can be restored with
    :meth:`rollback`.

    Args:
        max_versions: Maximum history depth per name.  When the limit is
                      reached the oldest version is evicted.  ``0`` means
                      unlimited.  Defaults to ``0``.

    Example::

        store = VersionedPromptStore()
        store.push("greeting", v1_template)   # version 1
        store.push("greeting", v2_template)   # version 2
        store.rollback("greeting")             # restores version 1
    """

    def __init__(self, max_versions: int = 0) -> None:
        self._history: dict[str, list[_VersionEntry]] = {}
        self._current: dict[str, int] = {}  # name → current version number
        self._max = max_versions

    def push(
        self,
        name: str,
        template: AbstractPromptTemplate,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Add a new version of *template* under *name*.

        Args:
            name: Unique template name.
            template: Template to store.
            metadata: Arbitrary metadata attached to this version.

        Returns:
            The new version number (1-based, incrementing).
        """
        history = self._history.setdefault(name, [])
        next_version = (history[-1].version + 1) if history else 1
        entry = _VersionEntry(next_version, template, metadata or {})
        history.append(entry)
        self._current[name] = next_version

        if self._max > 0 and len(history) > self._max:
            history.pop(0)

        return next_version

    def get(self, name: str) -> AbstractPromptTemplate:
        """Return the current (latest active) version of *name*.

        Args:
            name: Template name.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptNotFoundError`:
                *name* has never been pushed.
        """
        history = self._history.get(name)
        if not history:
            raise PromptNotFoundError(f"No template stored under '{name}'.")
        current_version = self._current[name]
        return self._find_entry(name, current_version).template

    def get_version(self, name: str, version: int) -> AbstractPromptTemplate:
        """Return a specific historical version.

        Args:
            name: Template name.
            version: 1-based version number.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptNotFoundError`:
                *name* is unknown.
            :class:`~lexigram.ai.prompt.exceptions.PromptVersionError`:
                *version* does not exist (may have been evicted).
        """
        return self._find_entry(name, version).template

    def rollback(self, name: str, steps: int = 1) -> AbstractPromptTemplate:
        """Roll back *steps* version(s) and return the restored template.

        Args:
            name: Template name.
            steps: Number of versions to roll back.  Defaults to ``1``.

        Returns:
            The restored (now current) template.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptVersionError`:
                Cannot roll back further than the oldest stored version.
        """
        if name not in self._current:
            raise PromptNotFoundError(f"No template stored under '{name}'.")

        history = self._history[name]
        current_index = next(
            i for i, e in enumerate(history) if e.version == self._current[name]
        )
        target_index = current_index - steps
        if target_index < 0:
            raise PromptVersionError(
                f"Cannot roll back {steps} step(s) for '{name}': "
                f"only {current_index} version(s) are available in history."
            )
        target = history[target_index]
        self._current[name] = target.version
        return target.template

    def list_versions(self, name: str) -> list[dict[str, Any]]:
        """Return metadata for all stored versions of *name* (oldest first).

        Args:
            name: Template name.

        Returns:
            List of ``{"version": int, "current": bool, "metadata": dict}`` dicts.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptNotFoundError`:
                *name* is unknown.
        """
        if name not in self._history:
            raise PromptNotFoundError(f"No template stored under '{name}'.")
        current_version = self._current[name]
        return [
            {
                "version": e.version,
                "current": e.version == current_version,
                "metadata": e.metadata,
            }
            for e in self._history[name]
        ]

    def _find_entry(self, name: str, version: int) -> _VersionEntry:
        history = self._history.get(name)
        if not history:
            raise PromptNotFoundError(f"No template stored under '{name}'.")
        for entry in history:
            if entry.version == version:
                return entry
        raise PromptVersionError(
            f"Version {version} of '{name}' is not available "
            f"(may have been evicted by max_versions={self._max})."
        )


__all__ = ["VersionedPromptStore"]
