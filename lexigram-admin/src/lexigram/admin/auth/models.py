"""Authentication models for Lexigram Admin.

This module re-exports admin user types for backwards-compatible access.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.auth.integration import AdminUser as AdminUser

# Re-export RoleDefinition — kept as Any until a concrete Role model is defined.
Role = Any

# Guest user sentinel — None means "not authenticated".
GUEST_USER = None
