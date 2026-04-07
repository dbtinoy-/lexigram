"""Weaviate vector collection implementation."""

from __future__ import annotations

from typing import Any
import uuid

from lexigram.contracts.data.vector import (
    DeleteResult,
    DistanceMetric,
    SearchQuery,
    SearchResult,
    UpsertResult,
    VectorRecord,
)
from lexigram.logging import get_logger
from lexigram.vector.backends.base import BaseVectorCollection

logger = get_logger(__name__)


class WeaviateCollection(BaseVectorCollection):
    """Weaviate vector collection implementation.

    Wraps a ``weaviate-client>=4.x`` collection object and translates
    results into framework-level vector types.

    Args:
        raw_collection: The Weaviate SDK collection handle (type-erased to
            avoid a hard import at module level).
        name: Collection name.
        dimension: Vector dimension.
        distance_metric: Distance metric used by the collection index.
    """

    def __init__(
        self,
        raw_collection: Any,
        name: str,
        dimension: int,
        distance_metric: DistanceMetric,
    ) -> None:
        super().__init__(name, dimension, distance_metric)
        self._col = raw_collection

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------

    async def upsert(self, records: list[VectorRecord]) -> UpsertResult:
        """Insert or update vector records in the collection.

        Uses the weaviate-client v4 batch insert path.  Each record's ``id``
        is stored as the Weaviate object UUID so round-trips preserve identity.

        Args:
            records: Vector records to upsert.

        Returns:
            :class:`~lexigram.contracts.data.vector.UpsertResult`.
        """
        try:
            import weaviate.classes.data as wcd  # type: ignore[import-not-found]

            objects = []
            for record in records:
                properties: dict[str, Any] = dict(record.metadata)
                if record.content:
                    properties["_content"] = record.content

                objects.append(
                    wcd.DataObject(
                        uuid=record.id,
                        properties=properties,
                        vector=record.vector,
                    )
                )

            response = await self._col.data.insert_many(objects)
            failed = len(response.errors) if hasattr(response, "errors") else 0
            upserted = len(records) - failed
            if failed:
                logger.warning(
                    "weaviate_upsert_partial_failure",
                    collection=self.name,
                    failed=failed,
                    succeeded=upserted,
                )
            return UpsertResult(upserted_count=upserted)

        except Exception as exc:  # noqa: BLE001  # SDK raises varied exceptions on batch errors
            raise RuntimeError(
                f"Weaviate upsert failed on collection {self.name!r}: {exc}"
            ) from exc

    async def add_texts(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> UpsertResult:
        records = [
            VectorRecord(
                id=ids[i] if ids else str(uuid.uuid4()),
                vector=embeddings[i],
                metadata=metadatas[i] if metadatas else {},
                content=text,
            )
            for i, text in enumerate(texts)
        ]
        return await self.upsert(records)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        """Perform approximate-nearest-neighbour search using a query vector.

        Args:
            query: Search parameters including the query vector, top-k limit,
                metadata filter, and score threshold.

        Returns:
            List of :class:`~lexigram.contracts.data.vector.SearchResult`
            ordered by descending relevance score.
        """
        try:
            import weaviate.classes.query as wcq  # type: ignore[import-not-found]

            return_props = wcq.MetadataQuery(
                distance=True,
                uuid=True,
            )

            near_vector = wcq.NearVectorQuery(
                near_vector=query.vector,
                distance=None if query.min_score is None else (1.0 - query.min_score),
            )

            compiled_filter = None
            if query.filter is not None:
                from lexigram.vector.backends.weaviate.filters import (
                    WeaviateFilterCompiler,
                )

                compiled_filter = WeaviateFilterCompiler().compile(query.filter)

            response = await self._col.query.near_vector(
                near_vector=query.vector,
                limit=query.top_k,
                return_metadata=return_props,
                include_vector=query.include_vectors,
                filters=compiled_filter,
            )
        except Exception as exc:  # noqa: BLE001  # SDK raises varied exceptions on query errors
            raise RuntimeError(
                f"Weaviate search failed on collection {self.name!r}: {exc}"
            ) from exc

        results: list[SearchResult] = []
        for obj in response.objects:
            props: dict[str, Any] = dict(obj.properties or {})
            content: str | None = props.pop("_content", None)

            # Weaviate returns distance; convert to similarity score.
            distance: float = (
                obj.metadata.distance
                if obj.metadata and obj.metadata.distance is not None
                else 0.0
            )
            score = max(0.0, 1.0 - distance)

            vector: list[float] | None = None
            if query.include_vectors and hasattr(obj, "vector") and obj.vector:
                raw_vec = obj.vector
                if isinstance(raw_vec, dict):
                    # Named-vector collections store vectors in a dict keyed by vector name.
                    raw_vec = next(iter(raw_vec.values()), None)
                vector = list(raw_vec) if raw_vec else None

            results.append(
                SearchResult(
                    id=str(obj.uuid),
                    score=score,
                    metadata=props,
                    vector=vector,
                    content=content,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Retrieval by ID
    # ------------------------------------------------------------------

    async def get(self, ids: list[str]) -> list[VectorRecord]:
        """Retrieve vector records by ID.

        Args:
            ids: List of Weaviate object UUIDs to fetch.

        Returns:
            Found :class:`~lexigram.contracts.data.vector.VectorRecord` objects
            (missing IDs are silently omitted).
        """
        records: list[VectorRecord] = []
        for obj_id in ids:
            try:
                obj = await self._col.data.get_by_id(
                    uuid=obj_id,
                    include_vector=True,
                )
                if obj is None:
                    continue
                props = dict(obj.properties or {})
                content: str | None = props.pop("_content", None)

                raw_vec = obj.vector
                if isinstance(raw_vec, dict):
                    raw_vec = next(iter(raw_vec.values()), None)
                vector: list[float] = list(raw_vec) if raw_vec else []

                records.append(
                    VectorRecord(
                        id=str(obj.uuid),
                        vector=vector,
                        metadata=props,
                        content=content,
                    )
                )
            except Exception as exc:  # noqa: BLE001  # SDK may raise on missing UUIDs
                logger.debug("weaviate_get_error", id=obj_id, error=str(exc))
        return records

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete(self, ids: list[str]) -> DeleteResult:
        """Delete vector records by UUID.

        Args:
            ids: Weaviate object UUIDs to remove.

        Returns:
            :class:`~lexigram.contracts.data.vector.DeleteResult`.
        """
        deleted = 0
        for obj_id in ids:
            try:
                await self._col.data.delete_by_id(uuid=obj_id)
                deleted += 1
            except Exception as exc:  # noqa: BLE001  # SDK raises on missing UUIDs; treat as already deleted
                logger.debug("weaviate_delete_skip", id=obj_id, error=str(exc))
        return DeleteResult(deleted_count=deleted)

    async def delete_by_filter(self, filter: Any) -> DeleteResult:  # noqa: A002
        """Delete records matching a metadata filter.

        Compiles the framework ``MetadataFilter`` to a Weaviate ``Filter``
        object and invokes ``delete_many``.

        Args:
            filter: A :class:`~lexigram.contracts.data.vector.filters.MetadataFilter`
                (``MetadataCondition`` or ``MetadataConditionGroup``) describing
                which records to delete.

        Returns:
            :class:`~lexigram.contracts.data.vector.DeleteResult` with
            ``deleted_count=0`` (Weaviate does not report exact counts on
            batch deletes).
        """
        from lexigram.vector.backends.weaviate.filters import WeaviateFilterCompiler

        compiled = WeaviateFilterCompiler().compile(filter)
        try:
            await self._col.data.delete_many(where=compiled)
        except Exception as exc:  # noqa: BLE001  # delete_many can raise on empty filters
            raise RuntimeError(
                f"Weaviate delete_by_filter failed on {self.name!r}: {exc}"
            ) from exc
        return DeleteResult(deleted_count=0)

    # ------------------------------------------------------------------
    # Count
    # ------------------------------------------------------------------

    async def count(self) -> int:
        """Return the total number of objects in the collection.

        Returns:
            Object count, or ``0`` if the aggregate query fails.
        """
        try:
            result = await self._col.aggregate.over_all(total_count=True)
            return result.total_count or 0
        except Exception as exc:  # noqa: BLE001  # SDK raises on empty collections
            logger.debug("weaviate_count_error", collection=self.name, error=str(exc))
            return 0

    # ------------------------------------------------------------------
    # Metadata update
    # ------------------------------------------------------------------

    async def update_metadata(self, record_id: str, metadata: dict[str, Any]) -> bool:
        """Update the properties of an existing Weaviate object.

        Args:
            record_id: UUID of the object to update.
            metadata: New property values (merged, not replaced).

        Returns:
            ``True`` on success, ``False`` if the object was not found.
        """
        try:
            await self._col.data.update(
                uuid=record_id,
                properties=metadata,
            )
            return True
        except Exception as exc:  # noqa: BLE001  # SDK raises on missing UUID or schema mismatch
            logger.debug("weaviate_update_metadata_error", id=record_id, error=str(exc))
            return False
