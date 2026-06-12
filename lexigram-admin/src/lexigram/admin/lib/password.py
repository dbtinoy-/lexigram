"""Password hashing helpers for admin user management."""

from __future__ import annotations

__all__ = ["hash_password"]


def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt.

    Bcrypt with 12 rounds is used.  A missing ``bcrypt`` package raises
    ``RuntimeError`` instead of degrading to an unsalted digest.

    Args:
        plain: Plain-text password string.

    Returns:
        Hashed password string suitable for storage.

    Raises:
        RuntimeError: When the ``bcrypt`` package is not installed.
    """
    try:
        import bcrypt
    except ImportError as exc:
        raise RuntimeError(
            "bcrypt unavailable — refusing to hash admin passwords without a KDF"
        ) from exc

    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")
