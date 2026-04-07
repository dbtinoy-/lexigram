"""Webhook secret generation utilities."""

from __future__ import annotations

import secrets


def generate_webhook_secret(length: int = 32) -> str:
    """Generate a cryptographically secure webhook secret.

    Returns a hex-encoded string of ``length`` random bytes.

    Args:
        length: Number of random bytes to generate. Output is 2x this length.

    Returns:
        Hex-encoded secret string.
    """
    return secrets.token_hex(length)


__all__ = ["generate_webhook_secret"]
