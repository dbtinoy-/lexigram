"""Root hook payload surface for lexigram-admin.

Defines canonical payload dataclasses for admin-panel hook points. Actual
hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AdminPanelStartedHook",
    "AdminPanelStoppedHook",
    "AdminResourceAccessedHook",
]


@dataclass(frozen=True, kw_only=True)
class AdminPanelStartedHook:
    """Payload fired after the admin panel has finished its startup sequence."""


@dataclass(frozen=True, kw_only=True)
class AdminPanelStoppedHook:
    """Payload fired after an orderly admin panel shutdown completes."""


@dataclass(frozen=True, kw_only=True)
class AdminResourceAccessedHook:
    """Payload fired when an admin resource page is accessed.

    Attributes:
        resource_name: Registered name of the admin resource (e.g. ``"User"``).
        action: CRUD action being performed (e.g. ``"list"``, ``"change"``).
        user_id: Identifier of the admin user performing the action.
    """

    resource_name: str
    action: str
    user_id: str
