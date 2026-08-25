"""
Direct SQL admin user store implementation.

SQL statements and row parsing live in the sibling query-builder modules
(:mod:`lexigram.admin.auth.store.user_sql`,
:mod:`lexigram.admin.auth.store.user_rows`); this store owns schema
bootstrap, transaction flow, and error handling.
"""

from __future__ import annotations

from typing import Any
import uuid

from lexigram.admin.auth.errors import SetupAlreadyCompletedError
from lexigram.admin.auth.store.user_rows import (
    CreatedUser,
    first_row,
    row_to_user,
)
from lexigram.admin.auth.store.user_sql import (
    claim_first_admin_params,
    claim_first_admin_sql,
    create_table_sql,
    insert_user_payload,
    insert_user_sql,
    table_exists_sql,
    update_user_payload,
    upsert_user_params,
    upsert_user_sql,
)
from lexigram.admin.sql_dialect import is_postgres
from lexigram.auth import PasswordHasher
from lexigram.contracts.auth import PasswordHasherProtocol
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


@inject
class DirectSQLAdminUserStore:
    """Simple store implementation for admin_users table using direct SQL.

    This class provides the subset of operations required by AdminAuthAdapter
    (create_user, get_user_by_username, update_user, delete_user).
    Renamed from AdminUserStore to avoid conflict with config-backed store.
    """

    def __init__(
        self,
        db_provider: DatabaseProviderProtocol,
        password_hasher: PasswordHasherProtocol | None = None,
    ) -> None:
        self.db_provider = db_provider
        self._password_hasher = password_hasher or PasswordHasher()
        self._initialized = False

    async def ensure_schema(self) -> None:
        """Ensure admin_users table exists (create if needed)."""
        if self._initialized:
            return

        try:
            # Table check (supports both Postgres and SQLite)
            db_type = getattr(self.db_provider, "database_type", "") or ""
            exists = False

            if db_type.lower() in ("postgres", "postgresql"):
                result = await self.db_provider.execute_query(
                    table_exists_sql(db_type), []
                )
                if hasattr(result, "rows") and result.rows:
                    exists = result.rows[0].get("exists", False)
                elif isinstance(result, list) and result:
                    exists = result[0].get("exists", False)
            else:
                # SQLite fallback
                result = await self.db_provider.execute_query(
                    table_exists_sql(db_type), []
                )
                # Direct check if result has any rows
                if hasattr(result, "rows"):
                    exists = len(result.rows) > 0
                elif isinstance(result, list):
                    exists = len(result) > 0
                else:
                    exists = bool(result)

            logger.debug("admin_users exists=%s (db_type=%s)", exists, db_type)

            if not exists:
                logger.info("Table 'admin_users' not found; creating it...")
                sql = create_table_sql(db_type)

                await self.db_provider.execute(sql, [])
                logger.info("✅ admin_users table created successfully")
            else:
                logger.debug("Table 'admin_users' already exists")

            self._initialized = True
        except Exception as _schema_err:  # noqa: BLE001 — schema setup may fail with DB-specific errors; log and propagate
            logger.exception("Failed to ensure admin_users table exists")
            raise

    async def list_users(self) -> list[Any]:
        """Return all admin users ordered by creation time.

        Returns:
            Mutable user record objects (same type as
            ``get_user_by_email``) — one per row, oldest first.
        """
        result = await self.db_provider.execute_query(
            "SELECT * FROM admin_users ORDER BY created_at",
            [],
        )
        rows = []
        if hasattr(result, "rows") and result.rows:
            rows = list(result.rows)
        elif isinstance(result, list):
            rows = result
        elif isinstance(result, dict):
            rows = [result]
        return [row_to_user(row) for row in rows]

    async def get_admin_count(self) -> int:
        """Count total admin users."""
        await self.ensure_schema()
        sql = "SELECT COUNT(*) as count FROM admin_users"
        result = await self.db_provider.execute_query(sql, [])

        if hasattr(result, "rows") and result.rows:
            return result.rows[0].get("count", 0)
        if isinstance(result, list) and result:
            return result[0].get("count", 0)
        if isinstance(result, dict):
            return result.get("count", 0)

        return 0

    async def create_user(
        self,
        name: str,
        email: str,
        hashed_password: str,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        **kwargs,  # Accept and ignore extra parameters like 'profile'
    ) -> Any:
        await self.ensure_schema()
        admin_id = str(uuid.uuid4())
        # SQLite cannot bind Python lists — store roles/permissions as JSON text.
        serialize_lists = not is_postgres(self.db_provider)
        payload = insert_user_payload(
            admin_id,
            name,
            email,
            hashed_password,
            roles,
            permissions,
            serialize_lists=serialize_lists,
        )

        db_type = getattr(self.db_provider, "database_type", "") or ""
        # Attempt an atomic upsert when running against Postgres to avoid races
        if db_type.lower() in ("postgres", "postgresql"):
            # Use RETURNING to fetch created/updated row atomically.
            sql = upsert_user_sql()
            params = upsert_user_params(
                admin_id, name, email, hashed_password, roles, permissions
            )
            try:
                result = await self.db_provider.execute(sql, params)
                # db_provider.execute() returns a QueryResult object
                if hasattr(result, "success") and not result.success:
                    raise RuntimeError(
                        f"UPSERT failed: {getattr(result, 'error_message', 'unknown error')}"
                    )
                # Extract row from QueryResult.rows
                row = None
                if hasattr(result, "rows") and result.rows:
                    row = result.rows[0]
                elif isinstance(result, list) and result:
                    row = result[0]
                elif isinstance(result, dict):
                    row = result

                if row:
                    logger.info("Created or updated admin user %s via upsert", name)
                    return CreatedUser(
                        str(row.get("id")),
                        str(row.get("name") or ""),
                        str(row.get("email") or ""),
                    )
            except Exception as _upsert_err:  # noqa: BLE001 — pragma: no cover - fallback path exercised by tests; DB upsert may raise DB-specific errors
                # Fall through to non-upsert approach below
                logger.exception(
                    "Postgres upsert for admin_users failed, falling back to insert"
                )

        # Fallback (DB-agnostic): try a manual insert with JSONB casts for Postgres,
        # falling back to execute_insert for other databases.
        try:
            if db_type.lower() in ("postgres", "postgresql"):
                fallback_result = await self.db_provider.execute(
                    insert_user_sql(),
                    upsert_user_params(
                        admin_id, name, email, hashed_password, roles, permissions
                    ),
                )
                if hasattr(fallback_result, "success") and not fallback_result.success:
                    raise RuntimeError(
                        f"Fallback INSERT failed: {getattr(fallback_result, 'error_message', 'unknown error')}"
                    )
            else:
                await self.db_provider.execute_insert("admin_users", payload)

            logger.info("Created admin user %s via AdminUserStore", name)
            return CreatedUser(admin_id, name, email)
        except Exception as e:  # noqa: BLE001 — duplicate-key detection requires inspecting the exception type from any DB driver
            # Handle duplicate-key errors by resolving existing user and updating if needed
            err_str = str(e).lower()
            from lexigram.contracts.exceptions import DuplicateKeyError

            if (
                isinstance(e, DuplicateKeyError)
                or "duplicate key" in err_str
                or "unique constraint" in err_str
            ):
                logger.info(
                    "AdminUserStore.create_user detected existing user for %s; resolving existing user",
                    name,
                )
                existing = None
                try:
                    existing = await self.get_user_by_email(email)
                except (RuntimeError, ValueError, OSError):
                    existing = None

                if existing:
                    # Optionally update roles/permissions/hashed_password
                    try:
                        # Populate missing attrs if provided
                        existing_roles = getattr(existing, "roles", []) or []
                        if existing_roles != (roles or []):
                            existing.roles = roles or []
                        existing_perms = getattr(existing, "permissions", []) or []
                        if existing_perms != (permissions or []):
                            existing.permissions = permissions or []

                        existing_hash = getattr(existing, "hashed_password", None)
                        if hashed_password and existing_hash != hashed_password:
                            existing.hashed_password = hashed_password
                        await self.update_user(existing)
                        logger.info(
                            "Updated existing admin user %s after duplicate create",
                            name,
                        )
                    except BaseException:
                        logger.exception(
                            "Failed to update existing admin user %s after duplicate create",
                            name,
                        )

                    # Return lightweight object
                    class _ExistingUser:
                        def __init__(self, uid: str, name: str, email: str) -> None:
                            self.user_id = uid
                            self.name = name
                            self.email = email

                    return _ExistingUser(
                        str(
                            getattr(
                                existing, "user_id", getattr(existing, "id", None) or ""
                            )
                        ),
                        str(existing.name or ""),
                        str(existing.email or ""),
                    )

            # Re-raise if it's some other error
            logger.exception(
                "DirectSQLAdminUserStore.create_user failed for %s",
                name,
            )
            raise

    async def claim_first_admin(
        self,
        name: str,
        email: str,
        hashed_password: str,
        roles: list[str],
    ) -> Result[Any, SetupAlreadyCompletedError]:
        """Atomically insert the first admin account only if none exists.

        Runs a single ``INSERT ... SELECT ... WHERE NOT EXISTS`` statement so
        that concurrent first-run submissions cannot both insert.

        Args:
            name: Display name.
            email: Unique email address — used as the login identifier.
            hashed_password: Pre-hashed credential.
            roles: Role strings for the new account.

        Returns:
            Ok(CreatedUser) when this call inserted the first admin account;
            ``Err(SetupAlreadyCompletedError)`` when the table already holds
            an admin account and nothing was inserted.
        """
        await self.ensure_schema()
        admin_id = str(uuid.uuid4())
        serialize_lists = not is_postgres(self.db_provider)

        sql = claim_first_admin_sql(serialize_lists=serialize_lists)
        params = claim_first_admin_params(
            admin_id,
            name,
            email,
            hashed_password,
            roles,
            serialize_lists=serialize_lists,
        )

        result = await self.db_provider.execute(sql, params)
        if hasattr(result, "success") and not result.success:
            raise RuntimeError(
                "claim_first_admin failed: "
                f"{getattr(result, 'error_message', 'unknown error')}"
            )

        # 1 inserted row → Ok; 0 rows → Err. Postgres reports the insert via
        # RETURNING-style rows, SQLite via row_count on the QueryResult.
        row = None
        if hasattr(result, "rows") and result.rows:
            row = result.rows[0]
        elif isinstance(result, list) and result:
            row = result[0]
        elif isinstance(result, dict):
            row = result

        inserted = bool(row) or getattr(result, "row_count", 0) > 0
        if not inserted:
            return Err(SetupAlreadyCompletedError())

        if row:
            return Ok(
                CreatedUser(
                    str(row.get("id")),
                    str(row.get("name") or ""),
                    str(row.get("email") or ""),
                )
            )
        return Ok(CreatedUser(admin_id, name, email))

    async def get_user_by_email(self, email: str) -> Any | None:
        await self.ensure_schema()

        sql = "SELECT * FROM admin_users WHERE email = ?"
        result = await self.db_provider.execute_query(sql, [email])
        logger.debug(
            "get_user_by_email result type: %s, result: %s",
            type(result),
            result,
        )

        row = first_row(result)
        logger.debug("Parsed row: %s", row)

        if not row:
            logger.debug("No user found with email: %s", email)
            return None

        logger.debug(
            "Found user by email: %s, is_active: %s, has_password: %s",
            email,
            row.get("is_active"),
            bool(row.get("hashed_password")),
        )

        return row_to_user(row)

    async def get_user_by_id(self, user_id: str) -> Any | None:
        await self.ensure_schema()

        sql = "SELECT * FROM admin_users WHERE id = ?"
        result = await self.db_provider.execute_query(sql, [user_id])
        row = first_row(result)

        if not row:
            logger.debug("No user found with id: %s", user_id)
            return None

        logger.debug(
            "Found user by id: %s, is_active: %s",
            user_id,
            row.get("is_active"),
        )

        return row_to_user(row)

    async def update_user(self, user: Any) -> None:
        await self.ensure_schema()
        # SQLite cannot bind Python lists — store roles/permissions as JSON text.
        serialize_lists = not is_postgres(self.db_provider)
        await self.db_provider.execute_update(
            "admin_users",
            update_user_payload(user, serialize_lists=serialize_lists),
            "id = ?",
            [user.user_id],
        )

    async def authenticate(self, email: str, password: str) -> Any | None:
        """Authenticate an admin user by email and bcrypt-hashed password.

        Args:
            email: Email address to look up.
            password: Plain-text password to verify against the stored hash.

        Returns:
            User object when credentials are valid and account is active,
            ``None`` otherwise.
        """
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not getattr(user, "is_active", True):
            return None
        hashed = getattr(user, "hashed_password", None)
        if not hashed:
            return None
        try:
            hashed_str = hashed.decode("utf-8") if isinstance(hashed, bytes) else hashed
            if await self._password_hasher.verify(password, hashed_str):
                return user
        except (ValueError, TypeError) as exc:
            logger.warning(
                "authenticate.password_check_failed", email=email, error=str(exc)
            )
        return None

    async def delete_user(self, user_id: str) -> None:
        await self.ensure_schema()
        await self.db_provider.execute_delete("admin_users", "id = ?", [user_id])

    async def get_by_id(self, admin_id: str) -> Any | None:
        """Alias for get_user_by_id — used by AdminAuthMiddleware."""
        return await self.get_user_by_id(admin_id)


__all__ = ["DirectSQLAdminUserStore"]
