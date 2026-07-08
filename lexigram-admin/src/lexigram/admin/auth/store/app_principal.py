"""AdminUserStoreProtocol over AdminPrincipalProviderProtocol.

Lets the panel run entirely against the application's own users
(spec D3) — no admin_users table involved. Delegate shape:

- get_user_by_email/id, list_users, get_admin_count -> provider lookups
  (mapping to AdminUserRecord with user_id=principal.user_id, roles,
  permissions, is_active; hashed_password="")
- create_user -> provider.create_principal(name, email, password=raw)
  (NOTE: AdminUserStoreProtocol.create_user receives a hashed_password;
  in app mode the adapter passes the raw value through as-is — the app's
  hashing policy owns verification; documented for implementers)
- update_user -> provider.update_principal + provider.sync_roles when
  roles changed
- delete_user -> provider.delete_principal
- authenticate -> provider.authenticate
- ensure_schema -> provider.ensure_schema (no-op passthrough)
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.auth.errors import SetupAlreadyCompletedError
from lexigram.admin.auth.user import AdminUserRecord
from lexigram.contracts.admin import AdminPrincipal, AdminPrincipalProviderProtocol
from lexigram.result import Err, Ok, Result


class AppPrincipalUserStoreAdapter:
    """Adapter implementing the admin store seam over the app's principal bridge."""

    def __init__(self, provider: AdminPrincipalProviderProtocol) -> None:
        self._provider = provider

    async def get_admin_count(self) -> int:
        """Return the count of principals exposed by the app (see protocol docs)."""
        return len(await self._provider.list_principals())

    async def ensure_schema(self) -> None:
        """Delegate schema ownership to the app provider (passthrough)."""
        await self._provider.ensure_schema()

    async def list_users(self) -> list[Any]:
        """Return all principals as admin user records (see protocol docs)."""
        return [self._to_record(p) for p in await self._provider.list_principals()]

    async def create_user(
        self,
        name: str,
        email: str,
        hashed_password: str,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Create a principal; the password value passes through as-is."""
        del permissions, kwargs
        created = await self._provider.create_principal(
            name, email, hashed_password, roles=roles
        )
        return self._to_record(created)

    async def get_user_by_email(self, email: str) -> Any | None:
        """Look up a principal by email (see protocol docs)."""
        for p in await self._provider.list_principals():
            if p.email == email:
                return self._to_record(p)
        return None

    async def claim_first_admin(
        self,
        name: str,
        email: str,
        hashed_password: str,
        roles: list[str],
    ) -> Result[Any, SetupAlreadyCompletedError]:
        """Create the first admin principal when the app exposes none.

        Atomicity is delegated to the app's principal provider — the app
        owns principal creation semantics in app mode.

        Args:
            name: Display name.
            email: Unique email address — used as the login identifier.
            hashed_password: Pre-hashed credential (passed through as-is,
                mirroring :meth:`create_user`).
            roles: Role strings for the new account.

        Returns:
            Ok(record) when this call created the first admin principal;
            ``Err(SetupAlreadyCompletedError)`` when the app already exposes
            at least one principal and nothing was created.
        """
        if await self.get_admin_count() > 0:
            return Err(SetupAlreadyCompletedError())
        created = await self._provider.create_principal(
            name, email, hashed_password, roles=roles
        )
        return Ok(self._to_record(created))

    async def get_user_by_id(self, user_id: str) -> Any | None:
        """Look up a principal by id (see protocol docs)."""
        p = await self._provider.principal_for(user_id)
        return self._to_record(p) if p else None

    async def update_user(self, user: Any) -> None:
        """Persist principal changes and sync roles through the provider."""
        await self._provider.update_principal(
            AdminPrincipal(
                user_id=user.user_id,
                name=getattr(user, "name", ""),
                email=getattr(user, "email", ""),
                roles=list(getattr(user, "roles", []) or []),
                permissions=list(getattr(user, "permissions", []) or []),
                is_active=bool(getattr(user, "is_active", True)),
            )
        )
        if hasattr(user, "roles") and user.roles is not None:
            await self._provider.sync_roles(user.user_id, list(user.roles))

    async def delete_user(self, user_id: str) -> None:
        """Delete a principal (see protocol docs)."""
        await self._provider.delete_principal(user_id)

    async def authenticate(self, email: str, password: str) -> Any | None:
        """Authenticate against the app's own users (see protocol docs)."""
        p = await self._provider.authenticate(email, password)
        return self._to_record(p) if p else None

    @staticmethod
    def _to_record(p: AdminPrincipal) -> AdminUserRecord:
        """Map a principal onto the admin store record shape."""
        return AdminUserRecord(
            user_id=p.user_id,
            email=p.email,
            name=p.name,
            hashed_password="",
            roles=list(p.roles),
            permissions=list(p.permissions),
            is_active=p.is_active,
        )


__all__ = ["AppPrincipalUserStoreAdapter"]
