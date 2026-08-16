"""Root hook payload surface for lexigram-nosql.

Defines canonical payload dataclasses for NoSQL backend lifecycle hook points.
Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "NoSQLConnectedHook",
    "NoSQLDisconnectedHook",
]


@dataclass(frozen=True, kw_only=True)
class NoSQLConnectedHook:
    """Payload fired when a NoSQL backend connection is established.

    Attributes:
        backend: Identifier of the backend that connected (e.g. ``"mongodb"``).
    """

    backend: str


@dataclass(frozen=True, kw_only=True)
class NoSQLDisconnectedHook:
    """Payload fired when a NoSQL backend connection is closed.

    Attributes:
        backend: Identifier of the backend that disconnected.
    """

    backend: str
