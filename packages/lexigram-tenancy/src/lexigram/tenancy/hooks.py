"""Tenancy lifecycle hooks.

Hook names follow the ``tenant.<event>`` convention.  Applications can
subscribe to these via the framework's hook registry.
"""

from __future__ import annotations

# Well-known hook names for tenancy lifecycle events.
TENANT_RESOLVED_HOOK: str = "tenant.resolved"
TENANT_PROVISIONED_HOOK: str = "tenant.provisioned"
TENANT_ACTIVATED_HOOK: str = "tenant.activated"
TENANT_SUSPENDED_HOOK: str = "tenant.suspended"
TENANT_DEACTIVATED_HOOK: str = "tenant.deactivated"
TENANT_CONFIG_CHANGED_HOOK: str = "tenant.config_changed"

__all__ = [
    "TENANT_ACTIVATED_HOOK",
    "TENANT_CONFIG_CHANGED_HOOK",
    "TENANT_DEACTIVATED_HOOK",
    "TENANT_PROVISIONED_HOOK",
    "TENANT_RESOLVED_HOOK",
    "TENANT_SUSPENDED_HOOK",
]
