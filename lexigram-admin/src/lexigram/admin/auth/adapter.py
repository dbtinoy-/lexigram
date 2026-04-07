"""Adapter to align lexigram-admin's YAML/config-driven admin users and roles
with the canonical `lexigram-auth` provider and role manager.

This keeps `AdminProvider` UX but delegates core authn/authz to `lexigram-auth`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts import (
    AuthorizerProtocol,
    AuthProviderProtocol,
    DatabaseProviderProtocol,
)
from lexigram.contracts.auth import PasswordHasherProtocol
from lexigram.contracts.exceptions import UnresolvableDependencyError
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerProtocol, ContainerResolverProtocol

try:
    from lexigram.admin.auth.session_manager import AdminSessionManager
    from lexigram.admin.auth.store import (
        AdminSessionSqlRepository,
        DirectSQLAdminUserStore,
    )
except ImportError:
    AdminSessionManager = None  # type: ignore[assignment, misc]
    AdminSessionSqlRepository = None  # type: ignore[assignment,misc]
    DirectSQLAdminUserStore = None  # type: ignore[assignment, misc]

logger = get_logger(__name__)


@inject
class AdminAuthAdapter:
    """Sync admin config (users + roles) into ``lexigram-auth`` components.

    Usage::

        adapter = AdminAuthAdapter(admin_auth_config)
        await adapter.register(container)
    """

    def __init__(
        self,
        auth_config: Any,
        authorization_service: AuthorizerProtocol,
    ) -> None:
        self.auth_config = auth_config
        self.authorization_service = authorization_service

    async def sync(self, container: ContainerProtocol) -> None:
        """Sync admin config (roles + users) into the core Auth system.

        This method should be called during the boot phase. It should NOT
        call container.singleton() as the container is likely frozen.
        """
        if not getattr(self.auth_config, "enabled", True):
            logger.info("AdminAuthAdapter: disabled via config; skipping sync")
            return

        # Resolve or create AuthProvider
        auth_provider: AuthProviderProtocol | None = None
        try:
            auth_provider = await container.resolve("AdminAuthProvider")
            logger.info("Found dedicated AdminAuthProvider in container; using it")
        except UnresolvableDependencyError:
            try:
                auth_provider = await container.resolve(AuthProviderProtocol)
                logger.info("Found existing global AuthProvider in container; using it")
            except UnresolvableDependencyError:
                raise RuntimeError(
                    "AuthProvider not found in container; please register one using the Provider pattern",
                ) from None

        # Sync roles into authorization_service
        logger.debug(
            "Starting role sync with config: %s",
            getattr(self.auth_config, "roles", {}),
        )
        if getattr(self.auth_config, "roles", None):
            for name, role_def in self.auth_config.roles.items():
                logger.debug("Syncing role: %s", name)
                if isinstance(role_def, dict):
                    permissions = role_def.get("permissions", [])
                else:
                    # RoleDefinition-like object
                    permissions = getattr(role_def, "permissions", []) or []
                self.authorization_service.create_role(name, list(permissions))  # type: ignore[attr-defined]
                for perm in permissions:
                    self.authorization_service.add_role_permission(name, perm)  # type: ignore[attr-defined]
                logger.debug(
                    "Registered admin role '%s' with permissions %s",
                    name,
                    permissions,
                )

        # Prefer an AbstractAdminUserStore backed by admin_users table to avoid
        # writing admin accounts into the application `users` table.
        admin_store = None
        try:
            # Try to resolve an explicit admin store if registered
            admin_store = await container.resolve(
                "lexigram.admin.auth.AbstractAdminUserStore",
            )
        except UnresolvableDependencyError:
            admin_store = None

        # If no explicit admin store was registered, try to construct one from DatabaseProvider
        if admin_store is None:
            try:
                db_provider = await container.resolve(DatabaseProviderProtocol)
                logger.debug("Resolved DatabaseProvider: %s", db_provider)
                if DirectSQLAdminUserStore:  # type: ignore[truthy-function]
                    admin_store = DirectSQLAdminUserStore(db_provider)
                    logger.info(
                        "Constructed AbstractAdminUserStore from DatabaseProvider for admin sync",
                    )
                else:
                    logger.warning(
                        "DirectSQLAdminUserStore not available (ImportError?); skipping construction",
                    )
            except UnresolvableDependencyError:
                logger.exception(
                    "Failed to construct AbstractAdminUserStore from DatabaseProvider",
                )
                admin_store = None

        # Choose the store to use for admin user operations. Prefer AbstractAdminUserStore if available.
        if admin_store is not None:
            # If we are using a dedicated AdminAuthProvider or even the global one,
            # we need to ensure its user_store is set to this admin_store if we want separation.
            if auth_provider is not None:
                auth_provider.user_store = admin_store
                logger.info(
                    "Updated AuthProvider user_store to AbstractAdminUserStore for separation",
                )

                # Attach AdminSessionManager using admin_sessions table (FK to admin_users)
                try:
                    if hasattr(admin_store, "db_provider") and admin_store.db_provider:
                        if AdminSessionManager and AdminSessionSqlRepository:  # type: ignore[truthy-function]
                            auth_provider.session_manager = AdminSessionManager(
                                AdminSessionSqlRepository(admin_store.db_provider),
                            )
                            logger.info(
                                "Attached AdminSessionManager to AuthProvider for admin user store",
                            )
                        else:
                            logger.warning(
                                "AdminSessionManager not available; skipping attachment",
                            )
                except (AttributeError, TypeError):
                    logger.exception(
                        "Failed to attach AdminSessionManager to AuthProvider for admin user store",
                    )

        # Auto-seeding of admin users from config has been removed in favor
        # of the one-time super admin registration flow (SetupModule).
        logger.info("AdminAuthAdapter: sync complete")

    def _is_duplicate_key_error(self, e: Exception) -> bool:
        """Check if exception is a duplicate key error."""
        err_str = str(e).lower()
        return "duplicate key" in err_str or "unique constraint" in err_str

    async def _find_user(
        self,
        store: Any,
        email: str,
    ) -> Any | None:
        """Find user by email."""
        try:
            return await store.get_user_by_email(email)
        except (
            ConnectionError,
            RuntimeError,
            ValueError,
            TypeError,
            AttributeError,
        ) as e:
            logger.debug("Store lookup failed for %s: %s", email, e)
            return None

    async def _log_audit_event(
        self,
        container: ContainerResolverProtocol,
        table: str,
        entity_id: str,
        action: str,
        values: dict | None = None,
    ) -> None:
        """Log an audit event if an audit logger is available."""
        try:
            audit_logger = await container.resolve("AuditLogger")
            if audit_logger:
                resource = f"{table}:{entity_id}"
                details = {
                    "action": action,
                    "table": table,
                    "entity_id": entity_id,
                    "values": values or {},
                }
                await audit_logger.log_change(
                    user_id="system",
                    resource=resource,
                    action=action,
                    details=details,
                )
        except UnresolvableDependencyError:
            pass
        except (OSError, ValueError, TypeError) as e:
            logger.debug("Optional audit logging failed: %s", e)

    async def create_user(
        self,
        container: ContainerResolverProtocol,
        username: str,
        email: str,
        password: str | None = None,
        hashed_password: str | None = None,
        roles: list | None = None,
        permissions: list | None = None,
    ) -> Any:
        """Create a new admin user via the configured AuthProvider/UI store.

        This is intentionally minimal — it delegates to the AuthProvider.create_user
        when available, otherwise falls back to user_store.create_user.
        """
        roles = roles or []
        permissions = permissions or []

        # Resolve or create AuthProvider
        auth_provider: AuthProviderProtocol | None = None
        try:
            auth_provider = await container.resolve(AuthProviderProtocol)
        except (ImportError, AttributeError, RuntimeError):
            auth_provider = None

        # Prefer user_store.create_user if available (auth providers don't own user creation)
        if auth_provider and getattr(auth_provider, "user_store", None):
            user_store = auth_provider.user_store
            try:
                _hasher = await container.resolve(PasswordHasherProtocol)
                _hashed = hashed_password or await _hasher.hash(password or "")
                created = await user_store.create_user(  # type: ignore[union-attr]
                    name=username,
                    email=email,
                    hashed_password=_hashed,
                    roles=roles,
                    permissions=permissions,
                )
                await self._log_audit_event(
                    container,
                    "admin_users",
                    getattr(created, "user_id", username),
                    "INSERT",
                    {"username": username, "email": email},
                )
                return created
            except Exception as e:  # noqa: BLE001 — duplicate-key detection inspects exception type from any DB driver
                # Check if it's a duplicate key error before re-raising
                if not isinstance(
                    e,
                    (
                        ConnectionError,
                        RuntimeError,
                        ValueError,
                        TypeError,
                        AttributeError,
                    ),
                ):
                    # Only check for duplicate if not one of the known types
                    if not self._is_duplicate_key_error(e):
                        raise

                # Handle duplicate key error
                if self._is_duplicate_key_error(e):
                    logger.info(
                        "user_store.create_user detected existing user for %s; loading existing user",
                        username,
                    )
                    existing = await self._find_user(user_store, email)
                    if existing:
                        if roles and set(getattr(existing, "roles", [])) != set(roles):
                            existing.roles = roles
                            try:
                                await user_store.update_user(existing)  # type: ignore[union-attr]
                            except (
                                ConnectionError,
                                RuntimeError,
                                ValueError,
                                TypeError,
                                AttributeError,
                            ):
                                logger.exception(
                                    "Failed to update roles for existing user %s",
                                    username,
                                )
                        return existing
                logger.exception("user_store.create_user failed for %s", username)
                raise

        raise RuntimeError(
            "No AuthProvider or user_store available to create user",
        ) from None

    async def delete_user(
        self, container: ContainerResolverProtocol, user_id: str
    ) -> None:
        """Remove a user via AuthProvider.delete_user or user_store.delete_user."""
        try:
            auth_provider = await container.resolve(AuthProviderProtocol)
        except (ImportError, AttributeError, RuntimeError):
            auth_provider = None

        if auth_provider and hasattr(auth_provider, "delete_user"):
            try:
                await auth_provider.delete_user(user_id)
            except (
                ConnectionError,
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
            ):
                logger.exception("AuthProvider.delete_user failed for %s", user_id)
                raise

        # Fallback to user_store
        if auth_provider and getattr(auth_provider, "user_store", None):
            try:
                await auth_provider.user_store.delete_user(user_id)
                logger.info("Deleted user %s via user_store", user_id)
                await self._log_audit_event(container, "admin_users", user_id, "DELETE")
            except (
                ConnectionError,
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
            ):
                logger.exception("user_store.delete_user failed for %s", user_id)
                raise
            else:
                return

        raise RuntimeError(
            "No AuthProvider or user_store available to delete user",
        ) from None


@inject
class AdminAuthServiceAdapter:
    """Bridges admin auth operations to ``lexigram-auth``'s ``AuthProviderProtocol``.

    Usage::

        adapter = AdminAuthServiceAdapter(auth_provider=real_provider)
        user = await adapter.verify_token(token)
    """

    def __init__(
        self,
        auth_provider: AuthProviderProtocol | None = None,
    ) -> None:
        self._provider = auth_provider or _NoOpAuthProvider()

    async def verify_token(self, token: str) -> dict[str, Any] | None:
        """Verify a JWT or session token via the auth provider.

        Args:
            token: The token string to verify.

        Returns:
            Decoded token claims dict, or ``None`` if verification fails.
        """
        try:
            result = await self._provider.verify_token(token)
            if hasattr(result, "is_ok") and result.is_ok():
                return result.unwrap() if hasattr(result, "unwrap") else result
            return None
        except Exception:  # noqa: BLE001
            logger.warning("admin.auth.token_verification_failed")
            return None

    async def get_user(self, user_id: str) -> Any | None:
        """Fetch a user by ID via the auth provider.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            The user object, or ``None`` if not found.
        """
        try:
            return await self._provider.get_user(user_id)
        except Exception:  # noqa: BLE001
            return None

    async def validate_session(self, token: str) -> Any | None:
        """Validate a session and return user info.

        Args:
            token: The session token to validate.

        Returns:
            User info dict, or ``None`` if invalid.
        """
        try:
            result = await self._provider.validate_session(token)  # type: ignore[union-attr]
            if hasattr(result, "is_ok") and result.is_ok():
                return result.unwrap() if hasattr(result, "unwrap") else result
            return result
        except Exception:  # noqa: BLE001
            return None


class _NoOpAuthProvider:
    """Fallback when lexigram-auth is not installed."""

    async def verify_token(self, token: str) -> Any:
        return None

    async def get_user(self, user_id: str) -> Any | None:
        return None

    async def validate_session(self, token: str) -> Any:
        return None


__all__ = ["AdminAuthAdapter", "AdminAuthServiceAdapter"]
