"""Hook payloads for the secrets/credential vault lifecycle.

Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "SecretAccessedHook",
    "SecretCreatedHook",
    "SecretDeletedHook",
    "SecretRotatedHook",
]


@dataclass(frozen=True, kw_only=True)
class SecretCreatedHook:
    """Payload fired when a new secret is stored.

    Attributes:
        key: The secret key that was created.
    """

    key: str


@dataclass(frozen=True, kw_only=True)
class SecretRotatedHook:
    """Payload fired when a secret is rotated to a new version.

    Attributes:
        key: The secret key that was rotated.
        new_version: The version number after rotation.
    """

    key: str
    new_version: int


@dataclass(frozen=True, kw_only=True)
class SecretDeletedHook:
    """Payload fired when a secret is deleted.

    Attributes:
        key: The secret key that was deleted.
    """

    key: str


@dataclass(frozen=True, kw_only=True)
class SecretAccessedHook:
    """Payload fired when a secret value is read.

    Attributes:
        key: The secret key that was accessed.
    """

    key: str
