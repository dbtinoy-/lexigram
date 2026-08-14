"""Admin contributor exceptions — raised during contributor action dispatch."""

from __future__ import annotations

from lexigram.contracts.admin.errors import AdminError


class ContributorPermissionError(AdminError):
    """Raised when a user lacks required permissions to execute a contributor action.

    Contains the contributor ID, action name, and the missing permissions.

    Args:
        contributor_id: Identifier of the contributor that owns the action.
        action_name: Name of the action that was attempted.
        missing_permissions: Permissions the user lacks.
    """

    _code: str = "LEX_ERR_ADMIN_020"

    def __init__(
        self,
        contributor_id: str,
        action_name: str,
        missing_permissions: frozenset[str],
    ) -> None:
        self.contributor_id = contributor_id
        self.action_name = action_name
        self.missing_permissions = missing_permissions
        super().__init__(
            f"Permission denied for action '{action_name}' on contributor "
            f"'{contributor_id}'. Missing: {missing_permissions}"
        )


class ContributorNotFoundError(AdminError):
    """Raised when a contributor ID cannot be found in the assembled dashboard.

    Args:
        contributor_id: The requested contributor ID that was not found.
    """

    _code: str = "LEX_ERR_ADMIN_021"

    def __init__(self, contributor_id: str) -> None:
        self.contributor_id = contributor_id
        super().__init__(f"Contributor '{contributor_id}' not found in dashboard.")


__all__ = [
    "ContributorNotFoundError",
    "ContributorPermissionError",
]
