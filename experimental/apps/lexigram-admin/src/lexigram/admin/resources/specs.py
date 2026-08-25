"""Integration spec builders for Admin Resources.

Translates the optional ``cacheable`` / ``searchable`` / ``resilient``
integration flags into their concrete spec objects. Composed into
:class:`~lexigram.admin.resources.base.Resource` via inheritance so
``cache_spec()`` / ``search_spec()`` / ``resilient_spec()`` remain part of
every resource's public surface.
"""

from __future__ import annotations

from typing import Any


class IntegrationSpecsMixin:
    """Builders that resolve integration flags into spec objects.

    Requires the composing class to provide the ``cacheable``,
    ``searchable``, ``resilient``, ``name``, and ``search_fields``
    attributes (defined by :class:`~lexigram.admin.resources.base.Resource`).
    """

    cacheable: bool | Any
    searchable: bool | Any
    resilient: bool | Any
    name: str | None
    search_fields: list[str]

    def cache_spec(self) -> Any:
        """Return a CacheableSpec or None based on the cacheable field."""
        if self.cacheable is False:
            return None
        if self.cacheable is True:
            from lexigram.admin.integrations.cache import CacheableSpec

            return CacheableSpec()
        return self.cacheable

    def search_spec(self) -> Any:
        """Return a SearchableSpec or None based on the searchable field."""
        if self.searchable is False:
            return None
        if self.searchable is True:
            from lexigram.contracts.search import SearchableSpec

            return SearchableSpec(
                index_name=self.name,
                fields=tuple(self.search_fields),
            )
        return self.searchable

    def resilient_spec(self) -> Any:
        """Return a ResilientSpec or None based on the resilient field."""
        if self.resilient is False:
            return None
        if self.resilient is True:
            from lexigram.admin.integrations.resilience import ResilientSpec

            return ResilientSpec()
        return self.resilient


__all__ = ["IntegrationSpecsMixin"]
