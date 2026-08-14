"""Security utilities for lexigram-admin."""

from __future__ import annotations

import re
from typing import Any

# Patterns for detecting sensitive data
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "bearer",
        "authorization",
        "auth",
        "credential",
        "private_key",
        "privatekey",
        "session_id",
        "sessionid",
        "cookie",
        "csrf",
        "ssn",
        "credit_card",
        "creditcard",
        "card_number",
    },
)


def mask_sensitive_data(
    data: Any,
    mask: str = "****",
    sensitive_keys: frozenset[str] | None = None,
) -> Any:
    """Mask sensitive data in a dictionary or nested structure.

    Args:
        data: Data to mask (dict, list, or primitive)
        mask: Mask string to use
        sensitive_keys: Custom set of sensitive key names

    Returns:
        Masked data with same structure

    Example:
        >>> mask_sensitive_data({"username": "john", "password": "secret123"})
        {'username': 'john', 'password': '****'}
    """
    keys_to_check = sensitive_keys or SENSITIVE_KEYS

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            # Check if key matches any sensitive pattern
            is_sensitive = any(s in key_lower for s in keys_to_check)
            if is_sensitive:
                result[key] = mask
            else:
                result[key] = mask_sensitive_data(value, mask, keys_to_check)
        return result
    if isinstance(data, list):
        return [mask_sensitive_data(item, mask, keys_to_check) for item in data]
    if isinstance(data, tuple):
        return tuple(mask_sensitive_data(item, mask, keys_to_check) for item in data)
    return data


def mask_string_secrets(text: str, mask: str = "****") -> str:
    """Mask common secret patterns in strings.

    Args:
        text: Text to mask
        mask: Mask string to use

    Returns:
        Masked text
    """
    # Bearer tokens
    text = re.sub(r"Bearer\s+[A-Za-z0-9_-]+", f"Bearer {mask}", text)
    # API keys (common format)
    text = re.sub(
        r'api[_-]?key["\']?\s*[:=]\s*["\']?[A-Za-z0-9_-]+',
        f"api_key={mask}",
        text,
        flags=re.I,
    )
    # Password in URLs
    return re.sub(r"://([^:]+):([^@]+)@", f"://\\1:{mask}@", text)
