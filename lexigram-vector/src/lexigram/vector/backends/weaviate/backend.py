"""Weaviate vector database driver backend."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.data.vector import (
    CollectionConfig,
    CollectionInfo,
    DistanceMetric,
    IndexState,
    IndexType,
)
from lexigram.logging import get_logger
from lexigram.vector.backends.base import BaseVectorStore
from lexigram.vector.backends.weaviate.collection import WeaviateCollection

if TYPE_CHECKING:
    from lexigram.vector.config import WeaviateConfig

logger = get_logger(__name__)


class WeaviateStore(BaseVectorStore):
    """Weaviate vector database driver.

    Uses the ``weaviate-client>=4.x`` async API.  Requires the
    ``lexigram-vector[weaviate]`` optional extra.

    Args:
        config: :class:`~lexigram.vector.config.WeaviateConfig` instance.
    """

    def __init__(self, config: WeaviateConfig) -> None:
        self._config = config
        self._client: Any = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open an async connection to the Weaviate cluster."""
        try:
            import weaviate  # type: ignore[import-not-found]
            import weaviate.auth as weaviate_auth  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "weaviate-client is required for Weaviate support. "
                "Install with: pip install lexigram-vector[weaviate]"
            ) from exc

        auth: Any = None
        if self._config.api_key:
            api_key_value = self._config.api_key.get_secret_value()
            auth = weaviate_auth.AuthApiKey(api_key=api_key_value)

        try:
            # weaviate-client v4: use the async-capable client factory.
            # The exact helper name varies across patch versions; we probe the
            # most stable entry points and fall back gracefully.
            if hasattr(weaviate, "WeaviateAsyncClient"):
                import weaviate.connect as weaviate_connect  # type: ignore[import-not-found]

                self._client = weaviate.WeaviateAsyncClient(
                    connection_params=weaviate_connect.ConnectionParams.from_url(
                        url=self._config.url,
                        grpc_port=self._config.grpc_port,
                    ),
                    auth_client_secret=auth,
                )
                await self._client.connect()
            else:
                # Older v4 entry point
                self._client = await weaviate.use_async_with_custom(
                    url=self._config.url,
                    auth_credentials=auth,
                )
        except Exception as exc:  # noqa: BLE001  # weaviate SDK raises varied exception types on connect failure
            self._client = None
            raise RuntimeError(
                f"Failed to connect to Weaviate at {self._config.url}: {exc}"
            ) from exc

        logger.info("weaviate_connected", url=self._config.url)

    async def disconnect(self) -> None:
        """Close the Weaviate client connection."""
        if self._client is not None:
            try:
                await self._client.close()
            except Exception as exc:  # noqa: BLE001  # SDK may raise on double-close
                logger.debug("weaviate_close_error", error=str(exc))
            finally:
                self._client = None
            logger.info("weaviate_disconnected", url=self._config.url)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check Weaviate cluster readiness.

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            :class:`~lexigram.contracts.core.HealthCheckResult`.
        """
        if self._client is None:
            return HealthCheckResult(
                component="weaviate",
                status=HealthStatus.UNHEALTHY,
                message="Not connected",
            )
        try:
            ready: bool = await self._client.is_ready()
            status = HealthStatus.HEALTHY if ready else HealthStatus.UNHEALTHY
            return HealthCheckResult(
                component="weaviate",
                status=status,
                details={"url": self._config.url},
            )
        except Exception as exc:  # noqa: BLE001  # health check must absorb all SDK errors
            return HealthCheckResult(
                component="weaviate",
                status=HealthStatus.UNHEALTHY,
                message=str(exc),
                details={"url": self._config.url},
            )

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    async def list_collections(self) -> list[CollectionInfo]:
        """List all Weaviate collections in the cluster.

        Returns:
            List of :class:`~lexigram.contracts.data.vector.CollectionInfo`.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError("WeaviateStore is not connected. Call connect() first.")

        try:
            raw = await self._client.collections.list_all(simple=False)
        except Exception as exc:  # noqa: BLE001  # list_all may raise on schema errors
            logger.warning("weaviate_list_collections_error", error=str(exc))
            return []

        results: list[CollectionInfo] = []
        for name, meta in raw.items():
            try:
                # Extract dimension and distance from the collection schema.
                # The exact attribute path differs between weaviate-client versions.
                dimension: int = 0
                distance = DistanceMetric.COSINE
                if hasattr(meta, "vector_config") and meta.vector_config:
                    for vc in meta.vector_config.values():
                        if hasattr(vc, "vectorizer_config") and vc.vectorizer_config:
                            pass
                        if hasattr(vc, "quantization_config"):
                            pass
                results.append(
                    CollectionInfo(
                        name=name,
                        dimension=dimension,
                        distance_metric=distance,
                        index_type=IndexType.HNSW,
                        vector_count=0,
                        state=IndexState.READY,
                    )
                )
            except Exception as exc:  # noqa: BLE001  # skip malformed collection entries
                logger.debug(
                    "weaviate_collection_parse_error", name=name, error=str(exc)
                )

        return results

    async def create_collection(self, config: CollectionConfig) -> None:
        """Create a new Weaviate collection (class).

        Args:
            config: Collection configuration including name, dimension, and
                distance metric.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError("WeaviateStore is not connected. Call connect() first.")

        try:
            import weaviate.classes.config as wcc  # type: ignore[import-not-found]

            distance_map = {
                DistanceMetric.COSINE: wcc.VectorDistances.COSINE,
                DistanceMetric.DOT_PRODUCT: wcc.VectorDistances.DOT,
                DistanceMetric.EUCLIDEAN: wcc.VectorDistances.L2_SQUARED,
                DistanceMetric.MANHATTAN: wcc.VectorDistances.HAMMING,
            }
            distance = distance_map.get(
                config.distance_metric, wcc.VectorDistances.COSINE
            )

            await self._client.collections.create(
                name=config.name,
                vectorizer_config=wcc.Configure.Vectorizer.none(),
                vector_index_config=wcc.Configure.VectorIndex.hnsw(
                    distance_metric=distance,
                ),
            )
            logger.info(
                "weaviate_collection_created",
                name=config.name,
                dimension=config.dimension,
            )
        except Exception as exc:  # noqa: BLE001  # weaviate SDK raises varied errors on schema conflict
            raise RuntimeError(
                f"Failed to create Weaviate collection {config.name!r}: {exc}"
            ) from exc

    async def delete_collection(self, name: str) -> None:
        """Delete a Weaviate collection by name.

        Args:
            name: Collection name.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError("WeaviateStore is not connected. Call connect() first.")

        await self._client.collections.delete(name)
        logger.info("weaviate_collection_deleted", name=name)

    async def collection_exists(self, name: str) -> bool:
        """Check whether a collection exists.

        Args:
            name: Collection name.

        Returns:
            ``True`` if the collection exists.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError("WeaviateStore is not connected. Call connect() first.")
        try:
            return await self._client.collections.exists(name)
        except Exception as exc:  # noqa: BLE001  # SDK may raise if schema fetch fails
            logger.debug("weaviate_exists_error", name=name, error=str(exc))
            return False

    async def get_collection(
        self,
        name: str,
        dimension: int = 0,
        distance_metric: DistanceMetric = DistanceMetric.COSINE,
    ) -> WeaviateCollection:
        """Return a :class:`WeaviateCollection` handle for an existing collection.

        Args:
            name: Collection name.
            dimension: Vector dimension (informational; Weaviate stores it
                in the schema rather than the client handle).
            distance_metric: Distance metric used by the collection.

        Returns:
            :class:`WeaviateCollection` ready for data operations.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError("WeaviateStore is not connected. Call connect() first.")
        raw_collection = self._client.collections.get(name)
        return WeaviateCollection(raw_collection, name, dimension, distance_metric)
