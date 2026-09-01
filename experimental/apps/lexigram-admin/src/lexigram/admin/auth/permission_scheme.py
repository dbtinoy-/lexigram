"""Canonical resource permission scheme for the admin panel (roadmap R6).

The admin's request-boundary authorization, navigation, and renderers all
derive resource permissions from ONE scheme defined here:

Canonical actions
    ``{resource}.view`` / ``{resource}.create`` / ``{resource}.update`` /
    ``{resource}.delete``

Legacy aliases (deprecated, still honoured during migration)
    ``{resource}.read`` and ``{resource}.list``  →  ``{resource}.view``
    ``{resource}.edit``                          →  ``{resource}.update``

Migration: re-issue grants using the canonical names. When a legacy alias
is the only grant that allows an action, a one-line deprecation warning
(``admin_authz.legacy_permission_grant``) is logged once per
``(resource, alias)`` pair per process. The aliases will be dropped in a
future minor version — treat the warning as a to-do, not an error.
"""

from __future__ import annotations

from lexigram.logging import get_logger

logger = get_logger(__name__)

#: The canonical per-resource CRUD actions, in display order.
CANONICAL_ACTIONS: tuple[str, ...] = ("view", "create", "update", "delete")

#: action -> legacy permission suffixes still honoured for that action.
LEGACY_ACTION_ALIASES: dict[str, tuple[str, ...]] = {
    "view": ("read", "list"),
    "update": ("edit",),
}

# (resource, alias) pairs already warned about — one line per process.
_warned_legacy_grants: set[tuple[str, str]] = set()


def permission_for(resource: str, action: str) -> str:
    """Return the canonical permission string for *action* on *resource*."""
    return f"{resource}.{action}"


def legacy_aliases_for(action: str) -> tuple[str, ...]:
    """Return the deprecated action suffixes still accepted for *action*."""
    return LEGACY_ACTION_ALIASES.get(action, ())


def candidate_permissions(resource: str, action: str) -> tuple[str, ...]:
    """All permission strings that currently grant *action* on *resource*.

    The canonical name always comes first; deprecated aliases follow so
    callers can detect which one matched and emit the deprecation warning
    via :func:`warn_legacy_grant`.
    """
    return (
        permission_for(resource, action),
        *(permission_for(resource, alias) for alias in legacy_aliases_for(action)),
    )


def warn_legacy_grant(resource: str, alias: str) -> None:
    """Log the one-line deprecation warning for a legacy grant, once.

    Called when a legacy alias (e.g. ``products.read``) was the grant that
    allowed an action. Deduplicated per ``(resource, alias)`` per process so
    boot/request logs stay readable.
    """
    key = (resource, alias)
    if key in _warned_legacy_grants:
        return
    _warned_legacy_grants.add(key)
    canonical = next(
        (
            action
            for action, aliases in LEGACY_ACTION_ALIASES.items()
            if alias in aliases
        ),
        "view",
    )
    logger.warning(
        "admin_authz.legacy_permission_grant",
        resource=resource,
        legacy_permission=permission_for(resource, alias),
        canonical_permission=permission_for(resource, canonical),
        hint="re-issue this grant with the canonical permission; "
        "legacy aliases will be removed in a future minor version",
    )


__all__ = [
    "CANONICAL_ACTIONS",
    "LEGACY_ACTION_ALIASES",
    "candidate_permissions",
    "legacy_aliases_for",
    "permission_for",
    "warn_legacy_grant",
]
