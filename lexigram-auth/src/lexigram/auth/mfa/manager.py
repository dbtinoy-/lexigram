"""MFA Manager — consolidated TOTP and backup-code management.

Stores MFA state in the user's ``profile['mfa']`` dict so no separate
MFA table is required.  Profile keys:

- ``enabled``: bool — whether TOTP is currently active
- ``secret``: base32-encoded TOTP secret
- ``backup_codes``: list of SHA-256 hex digests of the one-time codes
"""

from __future__ import annotations

import dataclasses
import hashlib
from typing import TYPE_CHECKING

from lexigram.auth.authn.mfa import (
    generate_backup_codes,
    generate_totp_secret,
    get_provisioning_uri,
    hash_backup_codes,
    verify_totp,
)
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.auth.storage.token_store import UserStoreProtocol

logger = get_logger(__name__)


@inject
class MFAManager:
    """Manages Multi-Factor Authentication (TOTP + backup codes) for users.

    MFA state is stored in the user profile so no dedicated MFA table is
    needed.  Injected via the DI container; the resolved ``UserStoreProtocol`` is
    used for all persistence.

    Args:
        user_store: The user store used to read and persist user profiles.
    """

    def __init__(self, user_store: UserStoreProtocol) -> None:
        self.user_store = user_store

    async def enable_totp(
        self,
        user_id: str,
        issuer: str = "lexigram",
    ) -> tuple[str, str, list[str]]:
        """Enable TOTP for a user and return enrollment credentials.

        A fresh TOTP secret and a set of backup codes are generated and
        stored (only the SHA-256 digests of backup codes are persisted).

        Args:
            user_id: The user to enable TOTP for.
            issuer: The issuer label shown in authenticator apps.

        Returns:
            A ``(secret, provisioning_uri, plain_backup_codes)`` tuple.
            Show the plain backup codes to the user once — they are not
            stored in plaintext.

        Raises:
            ValueError: If the user does not exist.
        """
        user = await self.user_store.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        secret = generate_totp_secret()
        account_name = user.name or user.email or user.user_id
        provisioning_uri = get_provisioning_uri(secret, account_name, issuer)
        backup_codes = generate_backup_codes()
        backup_hashes = hash_backup_codes(backup_codes)

        profile = dict(user.profile)
        profile_mfa = dict(profile.get("mfa") or {})
        profile_mfa.update(
            {"enabled": True, "secret": secret, "backup_codes": backup_hashes},
        )
        profile["mfa"] = profile_mfa
        updated = dataclasses.replace(user, profile=profile)
        await self.user_store.update_user(updated)

        return secret, provisioning_uri, backup_codes

    async def verify_totp(self, user_id: str, code: str) -> bool:
        """Verify a TOTP or backup code for a user.

        A backup code is consumed on first use — a second attempt with the
        same backup code returns ``False``.

        Args:
            user_id: The user to verify.
            code: A 6-digit TOTP code or a raw backup code string.

        Returns:
            ``True`` if the code is valid, ``False`` otherwise.
        """
        user = await self.user_store.get_user_by_id(user_id)
        if not user:
            return False

        mfa = user.profile.get("mfa") or {}
        if not mfa.get("enabled"):
            return False

        secret = mfa.get("secret")
        if secret and verify_totp(secret, code):
            return True

        # Check backup codes (single-use).
        backup_hashes = list(mfa.get("backup_codes") or [])
        code_hash = hashlib.sha256(str(code).encode("utf-8")).hexdigest()
        if code_hash in backup_hashes:
            backup_hashes.remove(code_hash)
            profile = dict(user.profile)
            profile_mfa = dict(profile.get("mfa") or {})
            profile_mfa["backup_codes"] = backup_hashes
            profile["mfa"] = profile_mfa
            updated = dataclasses.replace(user, profile=profile)
            await self.user_store.update_user(updated)
            return True

        return False

    async def disable_totp(self, user_id: str) -> bool:
        """Disable TOTP for a user.

        Args:
            user_id: The user to disable TOTP for.

        Returns:
            ``True`` if TOTP was disabled, ``False`` if the user does not exist.
        """
        user = await self.user_store.get_user_by_id(user_id)
        if not user:
            return False

        profile = dict(user.profile)
        profile_mfa = dict(profile.get("mfa") or {})
        profile_mfa.update({"enabled": False, "secret": None, "backup_codes": []})
        profile["mfa"] = profile_mfa
        updated = dataclasses.replace(user, profile=profile)
        await self.user_store.update_user(updated)
        return True

    def __repr__(self) -> str:
        """Return a string representation of this MFAManager."""
        return f"MFAManager(store={type(self.user_store).__name__})"


__all__ = ["MFAManager"]
