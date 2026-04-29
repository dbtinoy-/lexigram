"""Password hashing helpers for admin user management."""

from __future__ import annotations

import hashlib

__all__ = ["hash_password"]


def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt, falling back to SHA-256.

    Bcrypt with 12 rounds is the default.  SHA-256 is used only when the
    ``bcrypt`` package is not installed (e.g. lightweight test environments).

    Args:
        plain: Plain-text password string.

    Returns:
        Hashed password string suitable for storage.
    """
    try:
        import bcrypt

        hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12))
        return hashed.decode("utf-8")
    except ImportError:
        return hashlib.sha256(plain.encode()).hexdigest()
