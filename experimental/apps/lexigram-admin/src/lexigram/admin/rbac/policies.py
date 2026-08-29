"""Standard RBAC policies."""

from __future__ import annotations

from lexigram.admin.rbac.types import Policy, PolicyContext
from lexigram.primitives.registry import Registry


class PolicyRegistry(Registry[str, Policy]):
    """Registry of named policy functions.

    The in-package built-ins (``owner_only``, ``team_scoped``) are declared
    in :meth:`_default_entries`; applications can register additional
    policies or override a built-in at boot time.
    """

    def __init__(self) -> None:
        """Create an empty registry — use :meth:`with_defaults` for built-ins."""
        super().__init__(
            name="admin.rbac.policies",
            allow_overwrite=True,
        )

    @classmethod
    def _default_entries(cls) -> dict[str, Policy]:
        """Declare the complete in-package built-in policy set."""
        return {
            "owner_only": owner_only,
            "team_scoped": team_scoped,
        }


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


#: Module-level registry instance with the standard policies loaded.
_registry: PolicyRegistry = PolicyRegistry.with_defaults()


def register_policy(name: str, policy: Policy) -> None:
    """Register a policy by name."""
    _registry.register(name, policy)


def get_policy(name: str) -> Policy | None:
    """Get a policy by name."""
    return _registry.get(name)


__all__ = [
    "PolicyRegistry",
    "get_policy",
    "register_policy",
]
