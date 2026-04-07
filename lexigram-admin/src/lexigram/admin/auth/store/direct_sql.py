"""
Direct SQL admin user store implementation.
"""

from __future__ import annotations

from typing import Any
import uuid

from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class DirectSQLAdminUserStore:
    """Simple store implementation for admin_users table using direct SQL.

    This class provides the subset of operations required by AdminAuthAdapter
    (create_user, get_user_by_username, update_user, delete_user).
    Renamed from AdminUserStore to avoid conflict with config-backed store.
    """

    def __init__(self, db_provider: DatabaseProviderProtocol) -> None:
        self.db_provider = db_provider
        self._initialized = False

    async def _ensure_table_exists(self) -> None:
        """Ensure admin_users table exists (create if needed)."""
        if self._initialized:
            return

        try:
            # Table check (supports both Postgres and SQLite)
            db_type = getattr(self.db_provider, "database_type", "") or ""
            exists = False

            if db_type.lower() in ("postgres", "postgresql"):
                check_sql = "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'admin_users')"
                result = await self.db_provider.execute_query(check_sql, [])
                if hasattr(result, "rows") and result.rows:
                    exists = result.rows[0].get("exists", False)
                elif isinstance(result, list) and result:
                    exists = result[0].get("exists", False)
            else:
                # SQLite fallback
                check_sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='admin_users'"
                result = await self.db_provider.execute_query(check_sql, [])
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
                # Note: UUID in SQLite is TEXT, JSONB is TEXT
                sql = """
                    CREATE TABLE admin_users (
                        id VARCHAR(255) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        hashed_password TEXT,
                        roles TEXT,
                        permissions TEXT,
                        is_active BOOLEAN DEFAULT true,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                if db_type.lower() in ("postgres", "postgresql"):
                    sql = """
                        CREATE TABLE admin_users (
                            id VARCHAR(255) PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            email VARCHAR(255) UNIQUE NOT NULL,
                            hashed_password TEXT,
                            roles JSONB,
                            permissions JSONB,
                            is_active BOOLEAN DEFAULT true,
                            created_at TIMESTAMPTZ DEFAULT NOW(),
                            updated_at TIMESTAMPTZ DEFAULT NOW()
                        )
                    """

                await self.db_provider.execute(sql, [])
                logger.info("✅ admin_users table created successfully")
            else:
                logger.debug("Table 'admin_users' already exists")

            self._initialized = True
        except Exception as _schema_err:  # noqa: BLE001 — schema setup may fail with DB-specific errors; log and propagate
            logger.exception("Failed to ensure admin_users table exists")
            raise

    async def get_admin_count(self) -> int:
        """Count total admin users."""
        await self._ensure_table_exists()
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
        await self._ensure_table_exists()
        admin_id = str(uuid.uuid4())
        payload = {
            "id": admin_id,
            "name": name,
            "email": email,
            "hashed_password": hashed_password,
            "roles": roles or [],
            "permissions": permissions or [],
            "is_active": True,
        }

        # Attempt an atomic upsert when running against Postgres to avoid races
        db_type = getattr(self.db_provider, "database_type", "") or ""
        if db_type.lower() in ("postgres", "postgresql"):
            # Use RETURNING to fetch created/updated row atomically.
            # Explicit ::jsonb casts are required because asyncpg cannot
            # infer the column type for unparameterised JSONB columns
            # (DataError: expected str, got list).
            sql = (
                "INSERT INTO admin_users (id, name, email, hashed_password, roles, permissions, is_active) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (email) DO UPDATE SET "
                "name = EXCLUDED.name, hashed_password = EXCLUDED.hashed_password, "
                "roles = EXCLUDED.roles, permissions = EXCLUDED.permissions, is_active = EXCLUDED.is_active, updated_at = NOW() "
                "RETURNING id, name, email"
            )
            params = [
                admin_id,
                name,
                email,
                hashed_password,
                roles or [],
                permissions or [],
                True,
            ]
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

                    class _CreatedUser:
                        def __init__(self, uid: str, name: str, email: str) -> None:
                            self.user_id = uid
                            self.name = name
                            self.username = name
                            self.email = email

                    logger.info("Created or updated admin user %s via upsert", name)
                    return _CreatedUser(
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
                # Use explicit ::jsonb casts for Postgres
                fallback_sql = (
                    "INSERT INTO admin_users (id, name, email, hashed_password, roles, permissions, is_active) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)"
                )
                fallback_params = [
                    admin_id,
                    name,
                    email,
                    hashed_password,
                    roles or [],
                    permissions or [],
                    True,
                ]
                fallback_result = await self.db_provider.execute(
                    fallback_sql, fallback_params
                )
                if hasattr(fallback_result, "success") and not fallback_result.success:
                    raise RuntimeError(
                        f"Fallback INSERT failed: {getattr(fallback_result, 'error_message', 'unknown error')}"
                    )
            else:
                await self.db_provider.execute_insert("admin_users", payload)

            # Return lightweight created object similar shape used by adapter
            class _CreatedUser:  # type: ignore[no-redef]
                def __init__(self, uid: str, name: str, email: str) -> None:
                    self.user_id = uid
                    self.name = name
                    self.username = name
                    self.email = email

            logger.info("Created admin user %s via AdminUserStore", name)
            return _CreatedUser(admin_id, name, email)
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

    # Also need helper for email lookup if we use it in logic
    async def get_user_by_email(self, email: str) -> Any | None:
        await self._ensure_table_exists()
        from lexigram.logging import get_logger

        logger = get_logger(__name__)

        sql = "SELECT * FROM admin_users WHERE email = ?"
        result = await self.db_provider.execute_query(sql, [email])
        logger.debug(
            "get_user_by_email result type: %s, result: %s",
            type(result),
            result,
        )

        row = None
        if hasattr(result, "rows") and result.rows:
            row = result.rows[0]
        elif hasattr(result, "fetchone"):
            row = result.fetchone()
        elif isinstance(result, dict):
            row = result
        elif isinstance(result, list) and result:
            row = result[0] if result else None

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

        class _UserObj:
            def __init__(self, row: dict[str, Any]) -> None:
                self.user_id = str(row.get("id") or row.get("user_id"))
                self.name = row.get("name")
                self.email = row.get("email")
                # Add attributes needed for update
                self.roles = row.get("roles", [])
                self.permissions = row.get("permissions", [])
                self.hashed_password = row.get("hashed_password")
                self.is_active = row.get("is_active")

            def record_login(self) -> Any:
                """Record login - no-op for admin users"""

        return _UserObj(row)

    async def get_user_by_id(self, user_id: str) -> Any | None:
        await self._ensure_table_exists()
        from lexigram.logging import get_logger

        logger = get_logger(__name__)

        sql = "SELECT * FROM admin_users WHERE id = ?"
        result = await self.db_provider.execute_query(sql, [user_id])
        row = None
        if hasattr(result, "rows") and result.rows:
            row = result.rows[0]
        elif hasattr(result, "fetchone"):
            row = result.fetchone()
        elif isinstance(result, dict):
            row = result
        elif isinstance(result, list) and result:
            row = result[0]

        if not row:
            logger.debug("No user found with id: %s", user_id)
            return None

        logger.debug(
            "Found user by id: %s, is_active: %s",
            user_id,
            row.get("is_active"),
        )

        class _UserObj:
            def __init__(self, row: dict[str, Any]) -> None:
                self.user_id = str(row.get("id") or row.get("user_id"))
                self.name = row.get("name")
                self.email = row.get("email")
                self.roles = row.get("roles", [])
                self.permissions = row.get("permissions", [])
                self.hashed_password = row.get("hashed_password")
                self.is_active = row.get("is_active")

            def record_login(self) -> Any:
                """Record login - no-op for admin users"""

        return _UserObj(row)

    async def update_user(self, user: Any) -> None:
        await self._ensure_table_exists()
        payload = {
            "name": user.name,
            "email": user.email,
            "hashed_password": getattr(user, "hashed_password", None),
            "roles": getattr(user, "roles", []),
            "permissions": getattr(user, "permissions", []),
            "is_active": getattr(user, "is_active", True),
        }
        await self.db_provider.execute_update(
            "admin_users",
            payload,
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
            import bcrypt

            hashed_bytes = hashed.encode("utf-8") if isinstance(hashed, str) else hashed
            if bcrypt.checkpw(password.encode("utf-8"), hashed_bytes):
                return user
        except (ValueError, TypeError) as exc:
            logger.warning(
                "authenticate.password_check_failed", email=email, error=str(exc)
            )
        return None

    async def delete_user(self, user_id: str) -> None:
        await self._ensure_table_exists()
        await self.db_provider.execute_delete("admin_users", "id = ?", [user_id])

    async def get_by_id(self, admin_id: str) -> Any | None:
        """Alias for get_user_by_id — used by AdminAuthMiddleware."""
        return await self.get_user_by_id(admin_id)
