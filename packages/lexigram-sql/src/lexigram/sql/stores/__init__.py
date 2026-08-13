"""Database-backed store implementations for state, secrets, and locks.

These classes were previously housed in ``lexigram-cache`` as
``DatabaseBridge*`` classes but have been relocated here because they
depend on :class:`~lexigram.contracts.DatabaseProviderProtocol` — a purely
database concern — and sharing the connection pool with the rest of the
application is their defining feature.

They implement the protocols defined in
:mod:`lexigram.contracts.stores`:

- :class:`DatabaseStateStore` → :class:`~lexigram.contracts.stores.StateStoreProtocol`
- :class:`DatabaseSecretStore` → :class:`~lexigram.contracts.stores.AsyncSecretStoreProtocol`
- :class:`DatabaseLockStore`  → :class:`~lexigram.contracts.stores.LockStoreProtocol`
"""

from __future__ import annotations

from lexigram.sql.stores.locks import DatabaseLockStore
from lexigram.sql.stores.secrets import DatabaseSecretStore
from lexigram.sql.stores.state import DatabaseStateStore

__all__ = [
    "DatabaseLockStore",
    "DatabaseSecretStore",
    "DatabaseStateStore",
]
