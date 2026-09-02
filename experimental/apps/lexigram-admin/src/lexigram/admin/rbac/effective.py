"""Effective-permission resolution for the roles UI (R40, doc 36).

Pure, dependency-free mirror of the runtime authorizer's inheritance
semantics (lexigram-auth ``_check_mixin._get_effective_roles``): BFS
over ``inherits`` with a visited set (cycle-safe), missing parents
contribute nothing. Unlike the authorizer it keeps *provenance* — which
ancestor contributed each permission — so the UI can render "via role"
badges and warn about dangling inheritance references.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = ["EffectivePermissions", "resolve_effective_permissions"]


def _role_field(role: Any, name: str) -> list[str]:
    """Read a role field from an object attribute or dict key.

    Matches the authorizer's duck-typing so ``RoleDefinition`` objects
    and plain dicts resolve identically.
    """
    value = getattr(role, name, None)
    if value is None and isinstance(role, Mapping):
        value = role.get(name)
    return [str(v) for v in value] if value else []


@dataclass(frozen=True)
class EffectivePermissions:
    """Resolved permission set for one role, with provenance.

    Attributes:
        role: The role that was resolved.
        direct: The role's own permissions.
        inherited: Permission -> sorted tuple of ancestor roles that
            grant it. Permissions also granted directly are *not*
            listed here (direct wins; redundant grants are no error).
        ancestors: All resolved ancestor role names, sorted.
        missing: Referenced-but-not-stored role names, sorted. These
            grant nothing at runtime (fail-closed) but indicate a
            dangling ``inherits`` reference the operator should fix.
    """

    role: str
    direct: frozenset[str] = frozenset()
    inherited: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    ancestors: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()

    @property
    def all_permissions(self) -> frozenset[str]:
        """Direct and inherited permissions combined."""
        return self.direct | frozenset(self.inherited)


def resolve_effective_permissions(
    name: str,
    roles: Mapping[str, Any],
) -> EffectivePermissions:
    """Resolve a role's effective permissions across ``inherits`` chains.

    Args:
        name: Role to resolve. An unknown name resolves to an empty
            result with itself in ``missing``.
        roles: All stored roles keyed by name (``RoleDefinition``-like
            objects or plain dicts).

    Returns:
        Cycle-safe resolution mirroring runtime authorizer semantics.
    """
    target = roles.get(name)
    if target is None:
        return EffectivePermissions(role=name, missing=(name,))

    direct = frozenset(_role_field(target, "permissions"))

    inherited: dict[str, set[str]] = {}
    ancestors: set[str] = set()
    missing: set[str] = set()
    visited: set[str] = {name}
    queue: list[str] = _role_field(target, "inherits")

    while queue:
        parent_name = queue.pop(0)
        if parent_name in visited:
            continue
        visited.add(parent_name)
        parent = roles.get(parent_name)
        if parent is None:
            missing.add(parent_name)
            continue
        ancestors.add(parent_name)
        for perm in _role_field(parent, "permissions"):
            if perm not in direct:
                inherited.setdefault(perm, set()).add(parent_name)
        queue.extend(_role_field(parent, "inherits"))

    return EffectivePermissions(
        role=name,
        direct=direct,
        inherited={p: tuple(sorted(s)) for p, s in sorted(inherited.items())},
        ancestors=tuple(sorted(ancestors)),
        missing=tuple(sorted(missing)),
    )
