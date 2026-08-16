"""OAuth identity storage for linking users to OAuth providers.

This module provides storage abstractions for linking OAuth2 identities
to local user accounts. This enables "social login" where users can
authenticate using external identity providers.

Example:
    Implementing a custom OAuth identity store::

        from lexigram.auth.storage.oauth_identity_store import OAuthIdentityStore

        class MyOAuthStore(OAuthIdentityStore):
            async def create_oauth_identity(self, user_id, provider, provider_user_id):
                # Store the OAuth link
                return OAuthIdentity(...)

            async def get_oauth_identity(self, provider, provider_user_id):
                # Lookup by provider and external ID
                pass

            # ... implement other methods
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from lexigram.di.decorators import inject
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

logger = get_logger(__name__)


@runtime_checkable
class OAuthIdentityStore(Protocol):
    """Protocol for OAuth identity storage.

    OAuthIdentityStore manages the linking between local user accounts and
    external OAuth2 identity providers. This enables users to authenticate
    using social login while maintaining a consistent local user identity.

    Example:
        Using OAuth identity store::

            store = await container.resolve(OAuthIdentityStore)

            # Link OAuth identity to user
            identity = await store.create_oauth_identity(
                user_id="user-123",
                provider="google",
                provider_user_id="google-456"
            )

            # Find user by OAuth identity
            identity = await store.get_oauth_identity("google", "google-456")
            if identity:
                user = await store.get_user_by_oauth_identity(identity.id)
    """

    async def create_oauth_identity(
        self,
        user_id: str,
        provider: str,
        provider_user_id: str,
    ) -> OAuthIdentity:
        """Create an OAuth identity link for a user.

        Args:
            user_id: The local user ID to link the OAuth identity to.
            provider: The OAuth provider name (e.g., "google", "github").
            provider_user_id: The user's ID at the OAuth provider.

        Returns:
            The created OAuthIdentity instance.
        """
        ...

    async def get_oauth_identity(
        self,
        provider: str,
        provider_user_id: str,
    ) -> OAuthIdentity | None:
        """Get OAuth identity by provider and provider user ID.

        Args:
            provider: The OAuth provider name.
            provider_user_id: The user's ID at the OAuth provider.

        Returns:
            The OAuthIdentity if found, None otherwise.
        """
        ...

    async def get_oauth_identities_for_user(
        self,
        user_id: str,
    ) -> list[OAuthIdentity]:
        """Get all OAuth identities for a user"""
        ...

    async def delete_oauth_identity(
        self,
        provider: str,
        provider_user_id: str,
    ) -> bool:
        """Delete OAuth identity"""
        ...

    async def delete_oauth_identities_for_user(self, user_id: str) -> int:
        """Delete all OAuth identities for a user"""
        ...

    async def get_user_by_oauth_identity(
        self,
        provider: str,
        provider_user_id: str,
    ) -> str | None:
        """Get local user_id by OAuth provider and external user ID.

        This is the key method for resolving OAuth external IDs to local user IDs.
        Used when OAuth tokens contain non-UUID user identifiers (like Google's sub claim).

        Args:
            provider: The OAuth provider name (e.g., "google", "github", "apple").
            provider_user_id: The user's ID at the OAuth provider.

        Returns:
            The local user_id if found, None otherwise.
        """
        ...

    async def resolve_user_id(
        self,
        user_id_or_oauth_id: str,
        provider: str = "google",
    ) -> str | None:
        """Resolve a user_id that may be either a UUID or an OAuth external ID.

        This method handles the common issue where OAuth providers (like Google)
        use non-UUID identifiers (e.g., "101158382316025899191") which cannot
        be used directly in database queries expecting UUIDs.

        Resolution logic:
        1. If user_id_or_oauth_id is a valid UUID format, check if user exists
        2. If not a valid UUID, treat it as an OAuth provider_user_id and look up

        Args:
            user_id_or_oauth_id: Either a local user UUID or an OAuth provider's external ID.
            provider: The OAuth provider to search in (default: "google").

        Returns:
            The resolved local user_id if found, None otherwise.
        """
        ...


class OAuthIdentity:
    """OAuth identity linking user to provider"""

    def __init__(
        self,
        user_id: str,
        provider: str,
        provider_user_id: str,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.user_id = user_id
        self.provider = provider
        self.provider_user_id = provider_user_id
        self.created_at = created_at
        self.updated_at = updated_at


@inject
class SQLAlchemyOAuthIdentityStore(OAuthIdentityStore):
    """Database-backed OAuth identity store"""

    def __init__(self, db_provider: DatabaseProviderProtocol):
        self.db_provider = db_provider
        self._initialized = False

    async def _ensure_tables(self) -> None:
        """Ensure oauth_identities table exists."""
        if self._initialized:
            return

        create_sql = """
        CREATE TABLE IF NOT EXISTS oauth_identities (
            user_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_user_id TEXT NOT NULL,
            created_at DATETIME,
            updated_at DATETIME,
            PRIMARY KEY (provider, provider_user_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_oauth_identities_user_id ON oauth_identities(user_id);
        """

        async with self.db_provider.scoped_context():
            conn = await self.db_provider.get_scoped_connection()
            for statement in create_sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    await conn.execute(stmt)

        self._initialized = True

    async def _identity_from_row(self, row: Any) -> OAuthIdentity:
        """Convert database row to OAuthIdentity object"""
        return OAuthIdentity(
            user_id=row.get("user_id"),
            provider=row.get("provider"),
            provider_user_id=row.get("provider_user_id"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    async def create_oauth_identity(
        self,
        user_id: str,
        provider: str,
        provider_user_id: str,
    ) -> OAuthIdentity:
        """Create OAuth identity link"""
        await self._ensure_tables()

        identity = OAuthIdentity(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        insert_sql = """
        INSERT INTO oauth_identities
        (user_id, provider, provider_user_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """

        async with self.db_provider.scoped_context():
            conn = await self.db_provider.get_scoped_connection()
            await conn.execute(
                insert_sql,
                [
                    identity.user_id,
                    identity.provider,
                    identity.provider_user_id,
                    identity.created_at,
                    identity.updated_at,
                ],
            )

        logger.info("Created OAuth identity: user=%s, provider=%s", user_id, provider)
        return identity

    async def get_oauth_identity(
        self,
        provider: str,
        provider_user_id: str,
    ) -> OAuthIdentity | None:
        """Get OAuth identity by provider and provider user ID"""
        await self._ensure_tables()

        select_sql = """
        SELECT * FROM oauth_identities
        WHERE provider = ? AND provider_user_id = ?
        """

        async with self.db_provider.scoped_context():
            conn = await self.db_provider.get_scoped_connection()
            result = await conn.execute(select_sql, [provider, provider_user_id])
            row = result.rows[0] if result.rows else None

        return await self._identity_from_row(row) if row else None

    async def get_oauth_identities_for_user(
        self,
        user_id: str,
    ) -> list[OAuthIdentity]:
        """Get all OAuth identities for a user"""
        await self._ensure_tables()

        select_sql = "SELECT * FROM oauth_identities WHERE user_id = ?"

        async with self.db_provider.scoped_context():
            conn = await self.db_provider.get_scoped_connection()
            result = await conn.execute(select_sql, [user_id])
            rows = result.rows

        identities = []
        for row in rows:
            identity = await self._identity_from_row(row)
            identities.append(identity)

        return identities

    async def delete_oauth_identity(
        self,
        provider: str,
        provider_user_id: str,
    ) -> bool:
        """Delete OAuth identity"""
        await self._ensure_tables()

        delete_sql = """
        DELETE FROM oauth_identities
        WHERE provider = ? AND provider_user_id = ?
        """

        async with self.db_provider.scoped_context():
            conn = await self.db_provider.get_scoped_connection()
            result = await conn.execute(delete_sql, [provider, provider_user_id])
            deleted = bool(result.row_count > 0)  # Coerce to bool for typing stability

        if deleted:
            logger.info(
                "Deleted OAuth identity: provider=%s, user_id=%s",
                provider,
                provider_user_id,
            )

        return deleted

    async def delete_oauth_identities_for_user(self, user_id: str) -> int:
        """Delete all OAuth identities for a user"""
        await self._ensure_tables()

        delete_sql = "DELETE FROM oauth_identities WHERE user_id = ?"

        async with self.db_provider.scoped_context():
            conn = await self.db_provider.get_scoped_connection()
            result = await conn.execute(delete_sql, [user_id])
            deleted_count = int(result.row_count)

        if deleted_count > 0:
            logger.info(
                "Deleted %d OAuth identities for user %s",
                deleted_count,
                user_id,
            )

        return int(deleted_count)

    async def get_user_by_oauth_identity(
        self,
        provider: str,
        provider_user_id: str,
    ) -> str | None:
        """Get local user_id by OAuth provider and external user ID."""
        await self._ensure_tables()

        select_sql = """
        SELECT user_id FROM oauth_identities
        WHERE provider = ? AND provider_user_id = ?
        """

        async with self.db_provider.scoped_context():
            conn = await self.db_provider.get_scoped_connection()
            result = await conn.execute(select_sql, [provider, provider_user_id])
            row = result.rows[0] if result.rows else None

        return row.get("user_id") if row else None

    async def resolve_user_id(
        self,
        user_id_or_oauth_id: str,
        provider: str = "google",
    ) -> str | None:
        """Resolve user_id from either UUID or OAuth external ID.

        Resolution logic:
        1. If user_id_or_oauth_id is a valid UUID format, check if user exists
        2. If not a valid UUID, treat it as an OAuth provider_user_id and look up
        """
        import re

        # Check if it's a valid UUID format
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )

        is_uuid = bool(uuid_pattern.match(user_id_or_oauth_id))

        if is_uuid:
            # It's a UUID - check if user exists
            await self._ensure_tables()
            check_user_sql = "SELECT user_id FROM users WHERE user_id = ?"

            async with self.db_provider.scoped_context():
                conn = await self.db_provider.get_scoped_connection()
                result = await conn.execute(check_user_sql, [user_id_or_oauth_id])
                row = result.rows[0] if result.rows else None

            return row.get("user_id") if row else None
        # Not a UUID - treat as OAuth external ID
        return await self.get_user_by_oauth_identity(provider, user_id_or_oauth_id)

    def resolve_user_id_sync(
        self,
        external_id: str,
        provider: str = "google",
    ) -> str | None:
        """Synchronous resolution is not supported for database-backed store.

        This method is required by IdentityResolverProtocol but cannot be
        implemented safely for an async database provider.
        """
        logger.warning(
            "sync_resolution_not_supported",
            provider=provider,
            external_id=external_id,
            store="SQLAlchemyOAuthIdentityStore",
        )
        return None


@inject
class MongoDBOAuthIdentityStore(OAuthIdentityStore):
    """MongoDB-backed OAuth identity store"""

    def __init__(
        self,
        db_provider: DatabaseProviderProtocol,
        collection_name: str = "oauth_identities",
    ):
        self.db_provider = db_provider
        self.collection_name = collection_name
        self._initialized = False

    async def _ensure_collection(self) -> None:
        """Ensure collection exists with indexes"""
        if self._initialized:
            return

        collection = self.db_provider.db[self.collection_name]  # type: ignore[attr-defined]

        # Create indexes
        await collection.create_index([("user_id", 1)])
        await collection.create_index(
            [("provider", 1), ("provider_user_id", 1)],
            unique=True,
        )

        self._initialized = True

    async def _identity_from_doc(self, doc: dict[str, Any]) -> OAuthIdentity:
        """Convert MongoDB document to OAuthIdentity object"""
        return OAuthIdentity(
            user_id=doc["user_id"],
            provider=doc["provider"],
            provider_user_id=doc["provider_user_id"],
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )

    async def _doc_from_identity(self, identity: OAuthIdentity) -> dict[str, Any]:
        """Convert OAuthIdentity object to MongoDB document"""
        return {
            "user_id": identity.user_id,
            "provider": identity.provider,
            "provider_user_id": identity.provider_user_id,
            "created_at": identity.created_at,
            "updated_at": identity.updated_at,
        }

    async def create_oauth_identity(
        self,
        user_id: str,
        provider: str,
        provider_user_id: str,
    ) -> OAuthIdentity:
        """Create OAuth identity link"""
        await self._ensure_collection()

        identity = OAuthIdentity(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        doc = await self._doc_from_identity(identity)
        collection = self.db_provider.db[self.collection_name]  # type: ignore[attr-defined]
        await collection.insert_one(doc)

        logger.info("Created OAuth identity: user=%s, provider=%s", user_id, provider)
        return identity

    async def get_oauth_identity(
        self,
        provider: str,
        provider_user_id: str,
    ) -> OAuthIdentity | None:
        """Get OAuth identity by provider and provider user ID"""
        await self._ensure_collection()

        collection = self.db_provider.db[self.collection_name]  # type: ignore[attr-defined]
        doc = await collection.find_one(
            {"provider": provider, "provider_user_id": provider_user_id},
        )

        return await self._identity_from_doc(doc) if doc else None

    async def get_oauth_identities_for_user(
        self,
        user_id: str,
    ) -> list[OAuthIdentity]:
        """Get all OAuth identities for a user"""
        await self._ensure_collection()

        collection = self.db_provider.db[self.collection_name]  # type: ignore[attr-defined]
        cursor = collection.find({"user_id": user_id})

        identities = []
        async for doc in cursor:
            identity = await self._identity_from_doc(doc)
            identities.append(identity)

        return identities

    async def delete_oauth_identity(
        self,
        provider: str,
        provider_user_id: str,
    ) -> bool:
        """Delete OAuth identity"""
        await self._ensure_collection()

        collection = self.db_provider.db[self.collection_name]  # type: ignore[attr-defined]
        result = await collection.delete_one(
            {"provider": provider, "provider_user_id": provider_user_id},
        )

        deleted = bool(result.deleted_count > 0)
        if deleted:
            logger.info(
                "Deleted OAuth identity: provider=%s, user_id=%s",
                provider,
                provider_user_id,
            )

        return deleted

    async def delete_oauth_identities_for_user(self, user_id: str) -> int:
        """Delete all OAuth identities for a user"""
        await self._ensure_collection()

        collection = self.db_provider.db[self.collection_name]  # type: ignore[attr-defined]
        result = await collection.delete_many({"user_id": user_id})

        deleted_count = int(result.deleted_count)
        if deleted_count > 0:
            logger.info(
                "Deleted %d OAuth identities for user %s",
                deleted_count,
                user_id,
            )

        return deleted_count

    async def get_user_by_oauth_identity(
        self,
        provider: str,
        provider_user_id: str,
    ) -> str | None:
        """Get local user_id by OAuth provider and external user ID."""
        await self._ensure_collection()

        collection = self.db_provider.db[self.collection_name]  # type: ignore[attr-defined]
        doc = await collection.find_one(
            {"provider": provider, "provider_user_id": provider_user_id},
            {"user_id": 1},
        )

        return doc.get("user_id") if doc else None

    async def resolve_user_id(
        self,
        user_id_or_oauth_id: str,
        provider: str = "google",
    ) -> str | None:
        """Resolve user_id from either UUID or OAuth external ID.

        Resolution logic:
        1. If user_id_or_oauth_id is a valid UUID format, check if user exists
        2. If not a valid UUID, treat it as an OAuth provider_user_id and look up
        """
        import re

        # Check if it's a valid UUID format
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )

        is_uuid = bool(uuid_pattern.match(user_id_or_oauth_id))

        if is_uuid:
            # It's a UUID - check if user exists in users collection
            await self._ensure_collection()
            self.db_provider.db[self.collection_name]  # type: ignore[attr-defined]

            # We need to check the users collection - assume it's named "users"
            users_collection = self.db_provider.db["users"]  # type: ignore[attr-defined]
            user_doc = await users_collection.find_one(
                {"_id": user_id_or_oauth_id},
                {"_id": 1},
            )

            return user_doc.get("_id") if user_doc else None
        # Not a UUID - treat as OAuth external ID
        return await self.get_user_by_oauth_identity(provider, user_id_or_oauth_id)

    def resolve_user_id_sync(
        self,
        external_id: str,
        provider: str = "google",
    ) -> str | None:
        """Synchronous resolution is not supported for database-backed store."""
        logger.warning(
            "sync_resolution_not_supported",
            provider=provider,
            external_id=external_id,
            store="MongoDBOAuthIdentityStore",
        )
        return None


__all__ = [
    "MongoDBOAuthIdentityStore",
    "OAuthIdentity",
    "OAuthIdentityStore",
    "SQLAlchemyOAuthIdentityStore",
    "logger",
]
