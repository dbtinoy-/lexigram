"""Admin principal bridge — the app <-> panel identity seam (spec D3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class AdminPrincipal:
    """A panel-view of an application principal (Strapi-style dual identity)."""

    user_id: str
    name: str
    email: str
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    is_active: bool = True


@runtime_checkable
class AdminPrincipalProviderProtocol(Protocol):
    """Bridge implemented ONCE by the application; consumed by lexigram-admin.

    Distinct from ``RoleResolverProtocol`` (lexigram-web PEP for app-user API
    routes): this is the PANEL identity seam.
    """

    async def principal_for(self, user_id: str) -> AdminPrincipal | None: ...

    async def list_principals(self) -> list[AdminPrincipal]: ...

    async def create_principal(
        self, name: str, email: str, password: str, roles: list[str] | None = None
    ) -> AdminPrincipal: ...

    async def update_principal(self, principal: AdminPrincipal) -> None: ...

    async def delete_principal(self, user_id: str) -> None: ...

    async def authenticate(self, email: str, password: str) -> AdminPrincipal | None: ...

    async def sync_roles(self, user_id: str, roles: list[str]) -> None: ...

    async def ensure_schema(self) -> None: ...
