"""Testing client for lexigram-auth package.

This module provides testing utilities and clients for the lexigram-auth package,
integrating with the lexigram.testing infrastructure.

Note: This module now re-exports from the refactored testing package for backward compatibility.
"""

from __future__ import annotations

from lexigram.testing.clients.auth.bed import AuthTestBed
from lexigram.testing.clients.auth.test_client import (  # type: ignore[import-untyped]
    AuthTestClient,
)
from lexigram.testing.clients.auth.types import AuthTestToken, AuthTestUser

__all__ = [
    "AuthTestBed",
    "AuthTestClient",
    "AuthTestToken",
    "AuthTestUser",
]
