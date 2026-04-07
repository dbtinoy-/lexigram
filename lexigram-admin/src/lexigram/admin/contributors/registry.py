"""Contributor registry — registry-based dispatch for admin contributors."""

from __future__ import annotations

from collections.abc import Sequence

from lexigram.contracts.admin.protocols import AdminContributorProtocol


class ContributorRegistry:
    """Registry that collects and manages admin contributors.

    Follows the Registry pattern (AGENTS.md §6.3): empty ``__init__``,
    ``with_defaults()`` classmethod for pre-populated instances.
    """

    def __init__(self) -> None:
        self._contributors: dict[str, AdminContributorProtocol] = {}

    @classmethod
    def with_defaults(cls) -> ContributorRegistry:
        """Create a registry (no built-in contributors by default)."""
        return cls()

    def register(self, contributor: AdminContributorProtocol) -> None:
        """Register a contributor, keyed by its name."""
        self._contributors[contributor.name] = contributor

    def get(self, name: str) -> AdminContributorProtocol | None:
        """Get a contributor by name, or None."""
        return self._contributors.get(name)

    def get_all(self) -> Sequence[AdminContributorProtocol]:
        """Get all contributors sorted by priority (lower = first)."""
        return sorted(
            self._contributors.values(),
            key=_priority_or_default,
        )

    def get_by_group(self, group: str) -> Sequence[AdminContributorProtocol]:
        """Get contributors in a specific group, sorted by priority."""
        return sorted(
            [c for c in self._contributors.values() if c.group == group],
            key=_priority_or_default,
        )


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
