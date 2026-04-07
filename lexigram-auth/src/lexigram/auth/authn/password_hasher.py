"""Argon2id-based password hashing implementations.

This module provides:
- Argon2idKeyDerivation: implements KeyDerivationProtocol (core security)
- Argon2idPasswordHasher: implements PasswordHasherProtocol (auth-domain)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from lexigram.contracts.auth import PasswordHasherProtocol
from lexigram.contracts.security.protocols import KeyDerivationProtocol

if TYPE_CHECKING:
    from lexigram.auth.config import PasswordConfig

__all__ = ["Argon2idKeyDerivation", "Argon2idPasswordHasher"]


try:
    import argon2  # type: ignore[import-not-found]
    import argon2.exceptions  # type: ignore[import-not-found]

    _argon2 = argon2
    _argon2_available = True
except ImportError:
    _argon2 = None
    _argon2_available = False


class Argon2idKeyDerivation(KeyDerivationProtocol):
    """Argon2id key derivation implementation.

    Implements KeyDerivationProtocol using argon2-cffi.
    Follows OWASP 2024 recommendations for parameters.
    """

    def __init__(self, config: PasswordConfig | None = None) -> None:
        if not _argon2_available:
            raise RuntimeError("argon2-cffi is not installed")
        self._ph = _argon2.PasswordHasher(
            memory_cost=65536,  # 64 MiB
            time_cost=3,
            parallelism=4,
            hash_len=32,
            salt_len=16,
        )

    async def derive(self, secret: str, *, salt: bytes | None = None) -> str:
        """Derive a key from a secret using Argon2id."""

        def _derive_sync() -> str:
            return self._ph.hash(secret)

        return await asyncio.to_thread(_derive_sync)

    async def verify(self, secret: str, encoded: str) -> bool:
        """Verify a secret against an Argon2id hash."""

        def _verify_sync() -> bool:
            try:
                self._ph.verify(encoded, secret)
                return True
            except (
                _argon2.exceptions.VerifyMismatchError,
                _argon2.exceptions.VerificationError,
            ):
                return False

        return await asyncio.to_thread(_verify_sync)

    async def hash(self, secret: str, *, salt: bytes | None = None) -> str:
        """Backward-compatible alias for derive."""
        return await self.derive(secret, salt=salt)


class Argon2idPasswordHasher(PasswordHasherProtocol):
    """Auth-domain password hasher using Argon2id.

    Implements PasswordHasherProtocol (hash/verify) and delegates
    to KeyDerivationProtocol internally.
    """

    def __init__(self, kdf: KeyDerivationProtocol) -> None:
        self._kdf = kdf

    async def hash(self, password: str) -> str:
        """Hash a password using Argon2id."""
        return await self._kdf.derive(password)

    async def verify(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return await self._kdf.verify(password, hashed_password)
