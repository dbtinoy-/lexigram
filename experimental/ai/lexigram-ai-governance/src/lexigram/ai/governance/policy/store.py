"""Governance policy store — CRUD for named governance policies.

Stores policies in memory (default) or delegates to a database backend.
All writes are idempotent: adding a policy with the same name replaces the
existing one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.governance.policy.types import Policy

logger = get_logger(__name__)


class PolicyStore:
    """In-memory store for governance policies.

    Policies are keyed by :attr:`Policy.name`.  Lower-priority values are
    evaluated first by :class:`~engine.PolicyEngine` (policies are always
    returned sorted ascending by priority).

    Example::

        store = PolicyStore()
        store.add_policy(Policy(name="block-gpt4-free-tier", ...))
        policies = await store.get_policies(scope="api_user")
    """

    def __init__(self) -> None:
        """Initialize an empty policy store."""
        self._policies: dict[str, Policy] = {}

    async def get_policies(self, scope: str = "") -> list[Policy]:
        """Return all enabled policies sorted by priority.

        Args:
            scope: Optional role/scope filter.  When non-empty, only policies
                whose rules reference *scope* (or whose rule ``roles`` list is
                empty, meaning "all roles") are returned.

        Returns:
            Enabled policies sorted by ascending priority.
        """
        all_enabled = [p for p in self._policies.values() if p.enabled]

        if scope:
            filtered: list[Policy] = []
            for policy in all_enabled:
                for rule in policy.rules:
                    if not rule.roles or scope in rule.roles:
                        filtered.append(policy)
                        break
            all_enabled = filtered

        return sorted(all_enabled, key=lambda p: p.priority)

    async def add_policy(self, policy: Policy) -> None:
        """Add or replace a policy.

        Args:
            policy: Policy to store; replaces any existing policy with the
                same name.
        """
        self._policies[policy.name] = policy
        logger.info("policy_store_added", policy_name=policy.name)

    async def remove_policy(self, name: str) -> bool:
        """Remove a policy by name.

        Args:
            name: Policy name to remove.

        Returns:
            True if the policy existed and was removed, False if not found.
        """
        if name in self._policies:
            del self._policies[name]
            logger.info("policy_store_removed", policy_name=name)
            return True
        return False

    async def get_policy(self, name: str) -> Policy | None:
        """Retrieve a single policy by name.

        Args:
            name: Policy name.

        Returns:
            The policy if found, or ``None``.
        """
        return self._policies.get(name)

    def policy_count(self) -> int:
        """Return the number of stored policies."""
        return len(self._policies)


__all__ = ["PolicyStore"]
