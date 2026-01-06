"""Public protocol surface for ``lexigram.secrets``.

Re-exports the canonical ``RotatableSecretStoreProtocol`` along with
contract-level protocols relevant to secret management.
"""

from __future__ import annotations

from lexigram.contracts.security.stores import AsyncSecretStoreProtocol
from lexigram.secrets.tenancy import TenantScopedSecretStore
from lexigram.secrets.types import RotatableSecretStoreProtocol

__all__ = [
    "AsyncSecretStoreProtocol",
    "RotatableSecretStoreProtocol",
    "TenantScopedSecretStore",
]
