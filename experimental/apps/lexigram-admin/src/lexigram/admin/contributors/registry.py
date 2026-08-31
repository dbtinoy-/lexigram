"""Contributor registry — registry-based dispatch for admin contributors."""

from __future__ import annotations

from collections.abc import Sequence

from lexigram.contracts.admin.protocols import AdminContributorProtocol
from lexigram.primitives.registry import Registry


class ContributorRegistry(Registry[str, AdminContributorProtocol]):
    """Registry that collects and manages admin contributors.

    Follows the core Registry pattern: empty ``__init__`` and no in-package
    built-in set — contributors are registered explicitly by providers, so
    there is no ``with_defaults()``. Ordering follows each contributor's
    ``priority`` (lower = first) via the core ``priority_key`` hook.
    """

    def __init__(self) -> None:
        """Initialize an empty contributor registry.

        Duplicate names overwrite (last registration wins), matching the
        previous hand-rolled mapping semantics — contributor providers may
        re-register an upgraded instance during app bootstrapping.
        """
        super().__init__(
            name="admin.contributors",
            allow_overwrite=True,
            priority_key=_priority_or_default,
        )

    def add(self, contributor: AdminContributorProtocol) -> None:
        """Register a contributor, keyed by its name.

        Registering a duplicate name raises the core
        ``RegistryAlreadyExistsError``; use ``allow_overwrite=True`` on the
        core ``register()`` when an override is intended.
        """
        self.register(contributor.name, contributor)

    def get_all(self) -> Sequence[AdminContributorProtocol]:
        """Get all contributors sorted by priority (lower = first)."""
        return self.values_ordered()

    def get_by_group(self, group: str) -> Sequence[AdminContributorProtocol]:
        """Get contributors in a specific group, sorted by priority."""
        return [c for c in self.values_ordered() if c.group == group]


def _priority_or_default(contributor: AdminContributorProtocol) -> int:
    """Return contributor priority, or a high default when missing (mocks, tests)."""
    try:
        p = contributor.priority
        if not isinstance(p, int):
            return 9999
        return p
    except Exception:  # noqa: BLE001 — fallback for test doubles
        return 9999


__all__ = ["ContributorRegistry"]
