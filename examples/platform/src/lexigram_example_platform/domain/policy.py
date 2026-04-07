"""RBAC policy: role-based access control for platform resources.

This module defines the authorisation rules for the platform using a
**permission matrix** rather than ``if/elif`` chains.  Adding new
resources or actions is a data change, not a code change.

Usage::

    from lexigram_example_platform.domain.policy import can_access
    from lexigram_example_platform.domain.membership import Role

    if can_access(Role.ADMIN, "billing", "read"):
        ...

Wildcard semantics
------------------
- ``("*", "*")`` in a role's permission set means *allow everything*.
- ``(resource, "*")`` means *allow all actions on that resource*.
- An exact ``(resource, action)`` grants only that specific pairing.

Sentinel values
---------------
``WILDCARD_ALL = ("*", "*")`` and ``WILDCARD_ACTION = lambda r: (r, "*")``
are used only inside this module.  External callers always pass concrete
role / resource / action strings.
"""

from __future__ import annotations

from lexigram_example_platform.domain.membership import Role

# ---------------------------------------------------------------------------
# Permission matrix
#
# Each key is a Role; the value is a frozenset of (resource, action) tuples.
# The sentinel ("*", "*") grants unrestricted access to the role.
# The sentinel (resource, "*") grants all actions on a specific resource.
# ---------------------------------------------------------------------------

_WILDCARD: tuple[str, str] = ("*", "*")

_PERMISSIONS: dict[Role, frozenset[tuple[str, str]]] = {
    # OWNER — unrestricted; can do anything including transferring ownership.
    Role.OWNER: frozenset([_WILDCARD]),
    # ADMIN — full control over users, billing reads, and settings. Cannot
    # delete the tenant itself or transfer ownership.
    Role.ADMIN: frozenset(
        [
            ("users", "read"),
            ("users", "write"),
            ("users", "delete"),
            ("billing", "read"),
            ("billing", "write"),
            ("settings", "read"),
            ("settings", "write"),
            ("features", "read"),
            ("features", "write"),
            ("reports", "read"),
            ("reports", "write"),
            ("reports", "delete"),
        ]
    ),
    # MEMBER — read/write on core content; no billing or user management.
    Role.MEMBER: frozenset(
        [
            ("users", "read"),
            ("settings", "read"),
            ("features", "read"),
            ("reports", "read"),
            ("reports", "write"),
        ]
    ),
    # VIEWER — read-only across all non-privileged surfaces.
    Role.VIEWER: frozenset(
        [
            ("users", "read"),
            ("settings", "read"),
            ("features", "read"),
            ("reports", "read"),
        ]
    ),
}


def can_access(role: Role, resource: str, action: str) -> bool:
    """Determine whether *role* is permitted to perform *action* on *resource*.

    Evaluation order:

    1. ``("*", "*")`` wildcard → unconditional allow.
    2. ``(resource, "*")`` wildcard → allow all actions on that resource.
    3. Exact ``(resource, action)`` match.

    Args:
        role: The :class:`~lexigram_example_platform.domain.membership.Role`
            to evaluate.
        resource: Logical resource name (e.g. ``"billing"``, ``"users"``).
        action: Action identifier (e.g. ``"read"``, ``"write"``, ``"delete"``).

    Returns:
        ``True`` if the role is allowed; ``False`` otherwise (including for
        unknown roles not present in the permission matrix).

    Examples:
        >>> can_access(Role.OWNER, "billing", "delete")
        True
        >>> can_access(Role.VIEWER, "billing", "write")
        False
        >>> can_access(Role.ADMIN, "reports", "delete")
        True
    """
    allowed = _PERMISSIONS.get(role, frozenset())
    return (
        _WILDCARD in allowed
        or (resource, "*") in allowed
        or (resource, action) in allowed
    )


__all__ = ["can_access"]
