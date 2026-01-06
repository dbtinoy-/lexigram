"""Standard RBAC policies."""

from __future__ import annotations

from lexigram.admin.rbac.types import Policy, PolicyContext

_registry: dict[str, Policy] = {}


def register_policy(name: str, policy: Policy) -> None:
    """Register a policy by name."""
    _registry[name] = policy


def get_policy(name: str) -> Policy | None:
    """Get a policy by name."""
    return _registry.get(name)


# --- Standard Implementation Helpers ---


def owner_only(context: PolicyContext) -> bool:
    """Check if the user is the owner of the record."""
    if not context.record or not context.user:
        return False

    user_id = getattr(context.user, "id", getattr(context.user, "user_id", None))
    # Check common owner field names
    owner_id = (
        getattr(context.record, "user_id", None)
        or getattr(context.record, "owner_id", None)
        or getattr(context.record, "creator_id", None)
    )
    return user_id is not None and user_id == owner_id


def team_scoped(context: PolicyContext) -> bool:
    """Check if the user belongs to the same team as the record."""
    if not context.record or not context.user:
        return False

    user_team = getattr(context.user, "team_id", None)
    record_team = getattr(context.record, "team_id", None)

    return user_team is not None and user_team == record_team


# Register standard policies
register_policy("owner_only", owner_only)
register_policy("team_scoped", team_scoped)
