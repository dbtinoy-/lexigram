"""Google Cloud Firestore document store backend."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger
from lexigram.nosql.backends.base import AbstractDocumentStore
from lexigram.nosql.backends.firestore.repository import FirestoreRepository
from lexigram.nosql.exceptions import NoSQLConnectionError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from contextlib import AbstractAsyncContextManager

    from lexigram.nosql.config import FirestoreConfig

logger = get_logger(__name__)


class FirestoreBackend(AbstractDocumentStore):
    """Google Cloud Firestore async document store backend.

    Uses the ``google-cloud-firestore`` async client (``AsyncClient``).
    Requires the ``lexigram-nosql[firestore]`` optional extra.

    Features:

    - Async document CRUD via ``google.cloud.firestore_v1.AsyncClient``
    - Per-collection :class:`FirestoreRepository` handles with collection cache
    - Lightweight connectivity health check
    - Service-account JSON credentials (file path or inline JSON)

    Usage::

        backend = FirestoreBackend(config)
        await backend.connect()
        users = backend.collection("users")
        await users.insert_one({"name": "Alice"})
        await backend.disconnect()

    Args:
        config: :class:`~lexigram.nosql.config.FirestoreConfig` instance.
    """

    def __init__(self, config: FirestoreConfig) -> None:
        super().__init__(database_name=config.database_id)
        self._config = config
        self._client: Any = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Initialise the Firestore async client and verify connectivity."""
        try:
            from google.cloud import firestore_v1
        except ImportError as exc:
            raise NoSQLConnectionError(
                "google-cloud-firestore is required for Firestore support. "
                "Install with: pip install lexigram-nosql[firestore]"
            ) from exc

        kwargs: dict[str, Any] = {
            "project": self._config.project_id,
            "database": self._config.database_id,
        }

        if self._config.credentials_json:
            from google.oauth2 import service_account  # type: ignore[import-not-found]

            import lexigram.serialization as json

            creds_path = self._config.credentials_json
            # Support both file paths and raw JSON strings.
            if creds_path.strip().startswith("{"):
                info = json.loads(creds_path)
            else:
                with open(creds_path) as fh:  # noqa: PTH123
                    info = json.load(fh)

            kwargs["credentials"] = (
                service_account.Credentials.from_service_account_info(info)
            )

        try:
            self._client = firestore_v1.AsyncClient(**kwargs)
        except Exception as exc:
            raise NoSQLConnectionError(
                f"Failed to create Firestore client for project "
                f"{self._config.project_id!r}: {exc}"
            ) from exc

        # Verify connectivity with a lightweight probe.
        try:
            await asyncio.wait_for(
                self._probe_connectivity(),
                timeout=10.0,
            )
        except Exception as exc:
            self._client = None
            raise NoSQLConnectionError(
                f"Firestore connectivity check failed for project "
                f"{self._config.project_id!r}: {exc}"
            ) from exc

        self._connected = True
        logger.info(
            "nosql.firestore.connected",
            project=self._config.project_id,
            database=self._config.database_id,
        )

    async def _probe_connectivity(self) -> None:
        """Issue a minimal Firestore API call to verify credentials and network."""
        # List a single document from the root; this exercises auth + network
        # without requiring any specific collection to exist.
        col_ref = self._client.collections()
        async for _ in col_ref:  # noqa: S301  # iterate first element only
            break

    async def disconnect(self) -> None:
        """Close the Firestore client."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as exc:  # noqa: BLE001  # close may raise on already-closed transport
                logger.debug("nosql.firestore.close_error", error=str(exc))
            finally:
                self._client = None
                self._collections.clear()
                self._connected = False
            logger.info(
                "nosql.firestore.disconnected",
                project=self._config.project_id,
            )

    # ------------------------------------------------------------------
    # Collection access
    # ------------------------------------------------------------------

    def _create_collection(self, name: str) -> FirestoreRepository:  # type: ignore[override]
        """Return a :class:`FirestoreRepository` for *name*.

        Args:
            name: Firestore collection path (top-level or slash-delimited
                subcollection path, e.g. ``"users"`` or ``"users/uid/orders"``).

        Returns:
            :class:`FirestoreRepository` bound to the collection.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError(
                "FirestoreBackend is not connected. Call connect() first."
            )
        col_ref = self._client.collection(name)
        return FirestoreRepository(col_ref, name)

    def repository(self, collection_name: str) -> FirestoreRepository:
        """Return a :class:`FirestoreRepository` for *collection_name*.

        Repositories are cached so repeated calls with the same name return
        the same object without re-fetching the collection reference.

        Args:
            collection_name: Firestore collection path.

        Returns:
            :class:`FirestoreRepository` ready for CRUD operations.
        """
        return self.collection(collection_name)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Session (transactions)
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def _noop_session(self) -> AsyncIterator[None]:
        yield

    def session(self) -> AbstractAsyncContextManager[Any]:
        """Return an async context manager for a Firestore transaction.

        Note:
            Full transactional support requires using the Firestore
            ``AsyncTransactional`` decorator directly.  This session context
            provides a no-op placeholder compatible with
            :class:`~lexigram.nosql.backends.base.AbstractDocumentStore`.
        """
        return self._noop_session()

    # ------------------------------------------------------------------
    # Collection listing / dropping
    # ------------------------------------------------------------------

    async def list_collections(self) -> list[str]:
        """List all top-level collection names.

        Returns:
            Collection names, or an empty list if connectivity fails.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError(
                "FirestoreBackend is not connected. Call connect() first."
            )
        names: list[str] = []
        async for col_ref in self._client.collections():
            names.append(col_ref.id)
        return names

    async def drop_collection(self, name: str) -> None:
        """Delete all documents in a Firestore collection.

        Firestore has no single DROP COLLECTION command; this method
        iterates and bulk-deletes all documents in batches of 500.

        Args:
            name: Collection path to drop.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError(
                "FirestoreBackend is not connected. Call connect() first."
            )
        col_ref = self._client.collection(name)
        batch_size = 500
        async for snapshot in col_ref.limit(batch_size).stream():
            await snapshot.reference.delete()

        self._collections.pop(name, None)
        logger.info("nosql.firestore.collection_dropped", collection=name)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Verify Firestore connectivity with a lightweight list-collections probe.

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            :class:`~lexigram.contracts.core.HealthCheckResult`.
        """
        if not self._client or not self._connected:
            return HealthCheckResult(
                component="firestore",
                status=HealthStatus.UNHEALTHY,
                message="Not connected",
            )
        try:
            await asyncio.wait_for(self._probe_connectivity(), timeout=timeout)
            return HealthCheckResult(
                component="firestore",
                status=HealthStatus.HEALTHY,
                details={
                    "project": self._config.project_id,
                    "database": self._config.database_id,
                },
            )
        except TimeoutError:
            return HealthCheckResult(
                component="firestore",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {timeout}s",
            )
        except Exception as exc:  # noqa: BLE001  # health check must absorb all SDK errors
            return HealthCheckResult(
                component="firestore",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {exc}",
            )


__all__ = ["FirestoreBackend"]
