"""API Key Management for Lexigram Auth."""

from __future__ import annotations

from datetime import datetime, timedelta
import secrets
import string

from lexigram.auth.authn.security import PasswordHasher
from lexigram.auth.models.apikey import APIKey
from lexigram.contracts.auth import APIKeyRepositoryProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class APIKeyManager:
    """Manages API keys for service-to-service authentication.

    API keys follow the format: ``{prefix}_{random}`` — e.g. ``sk_live_abc123``.
    All persistence is delegated to an injected ``APIKeyRepositoryProtocol``; this
    class contains only key-management business logic.
    """

    KEY_LENGTH = 32
    DISPLAY_PREFIX_LENGTH = 8

    def __init__(self, repo: APIKeyRepositoryProtocol) -> None:
        """Initialise with the API key repository.

        Args:
            repo: Persistence abstraction for API key records.  Injected by
                the DI container; typically backed by ``APIKeySqlRepository``.
        """
        self._repo = repo

    def generate_raw_key(self, prefix: str = "sk_live") -> str:
        """Generate a cryptographically secure random API key.

        Args:
            prefix: Human-readable key family prefix (e.g. ``sk_live``).

        Returns:
            Full raw key string in ``{prefix}_{random}`` format.
        """
        alphabet = string.ascii_letters + string.digits
        key = "".join(secrets.choice(alphabet) for _ in range(self.KEY_LENGTH))
        return f"{prefix}_{key}"

    async def create_key(
        self,
        user_id: str,
        name: str,
        scopes: list[str] | None = None,
        expires_days: int | None = 365,
        prefix: str = "sk_live",
    ) -> tuple[str, APIKey]:
        """Create a new API key and persist its hash via the repository.

        Args:
            user_id: Owner of the API key.
            name: Human-readable label for the key.
            scopes: Optional list of permission scopes.
            expires_days: Days until expiry (``None`` for non-expiring keys).
            prefix: Key family prefix written into the display prefix field.

        Returns:
            ``(raw_key, api_key_object)`` — the raw key is only returned once.
        """
        raw_key = self.generate_raw_key(prefix)
        key_hash = await PasswordHasher.hash(raw_key)
        display_prefix = raw_key[: self.DISPLAY_PREFIX_LENGTH]

        expires_at: datetime | None = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)

        payload = {
            "name": name,
            "key_hash": key_hash,
            "prefix": display_prefix,
            "user_id": user_id,
            "scopes": scopes or [],
            "expires_at": expires_at,
        }

        key_id = await self._repo.insert(payload)

        api_key = APIKey(
            key_id=key_id,
            name=name,
            key_hash=key_hash,
            prefix=display_prefix,
            user_id=user_id,
            scopes=scopes or [],
            expires_at=expires_at,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        logger.info("Created API key for user %s: %s", user_id, name)
        return raw_key, api_key

    async def validate_key(
        self,
        raw_key: str,
        ip_address: str | None = None,
    ) -> APIKey | None:
        """Validate a raw API key and refresh its last-used metadata.

        Uses prefix pre-filtering for O(small) constant-time hash comparisons
        even with a large keyspace.

        Args:
            raw_key: Full plain-text API key submitted by the caller.
            ip_address: Originating IP for audit metadata (optional).

        Returns:
            Hydrated ``APIKey`` on success, ``None`` on invalid/expired key.
        """
        display_prefix = raw_key[: self.DISPLAY_PREFIX_LENGTH]
        rows = await self._repo.find_by_prefix(display_prefix)

        for row in rows:
            if await PasswordHasher.verify(raw_key, row["key_hash"]):
                expires_at = row.get("expires_at")
                if expires_at and expires_at < datetime.now():
                    logger.warning("Expired API key attempt: %s", row["id"])
                    continue

                await self._repo.update_last_used(row["id"], ip_address)

                return APIKey(
                    key_id=str(row["id"]),
                    name=row["name"],
                    key_hash=row["key_hash"],
                    prefix=row["prefix"],
                    user_id=str(row["user_id"]),
                    scopes=row["scopes"],
                    expires_at=expires_at,
                    last_used_at=datetime.now(),
                    last_used_ip=ip_address,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

        return None

    async def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key permanently.

        Args:
            key_id: Identifier of the key to revoke.

        Returns:
            ``True`` after successful revocation.
        """
        await self._repo.revoke(key_id)
        logger.info("Revoked API key: %s", key_id)
        return True

    async def list_keys(self, user_id: str) -> list[APIKey]:
        """List all active, non-revoked API keys for a user.

        Args:
            user_id: Owner identifier.

        Returns:
            List of hydrated ``APIKey`` objects.
        """
        rows = await self._repo.find_by_user(user_id)
        return [
            APIKey(
                key_id=str(row["id"]),
                name=row["name"],
                key_hash=row["key_hash"],
                prefix=row["prefix"],
                user_id=str(row["user_id"]),
                scopes=row["scopes"],
                expires_at=row.get("expires_at"),
                last_used_at=row.get("last_used_at"),
                last_used_ip=row.get("last_used_ip"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]


__all__ = ["APIKeyManager"]
