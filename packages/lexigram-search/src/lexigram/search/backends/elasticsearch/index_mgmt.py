"""Index-management and bulk operations for the Elasticsearch backend.

Helpers for index lifecycle (creation with mappings, settings updates,
rename via reindex) and bulk delete response parsing. Consumed by
:class:`~lexigram.search.backends.elasticsearch.backend.ElasticsearchBackend`.
"""

from __future__ import annotations

from typing import Any

from lexigram.logging import get_logger
from lexigram.search.config import ElasticsearchConfig

logger = get_logger(__name__)


async def ensure_index(
    client: Any,
    full_index: str,
    es_config: ElasticsearchConfig,
) -> None:
    """Ensure the index exists, creating it with mappings when missing."""
    # Check if index exists
    exists = await client.indices.exists(index=full_index)

    if not exists:
        # Create index with mappings
        mappings = {
            "properties": {
                "title": {"type": "text", "analyzer": "standard"},
                "name": {"type": "text", "analyzer": "standard"},
                "description": {"type": "text", "analyzer": "standard"},
                "content": {"type": "text", "analyzer": "standard"},
                "text": {"type": "text", "analyzer": "standard"},
                "body": {"type": "text", "analyzer": "standard"},
                "tags": {"type": "keyword"},
                "category": {"type": "keyword"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
            },
        }

        settings = {
            "number_of_shards": es_config.number_of_shards,
            "number_of_replicas": es_config.number_of_replicas,
            "analysis": {
                "analyzer": {
                    "custom_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"],
                    },
                },
            },
        }

        await client.indices.create(
            index=full_index,
            mappings=mappings,
            settings=settings,
        )


async def update_index_settings(
    client: Any,
    full_index: str,
    index: str,
    settings: dict[str, Any],
) -> dict[str, Any]:
    """Update index settings for an existing index.

    Args:
        client: Elasticsearch client.
        full_index: Fully-qualified index name (prefix included).
        index: The user-facing index name (used in logs).
        settings: Dictionary of settings to update (e.g., number_of_replicas).

    Returns:
        Dictionary with the update result.

    Raises:
        Exception: Re-raised from the transport after logging.
    """
    try:
        response = await client.indices.put_settings(
            index=full_index,
            body=settings,
        )
        return {"acknowledged": response.get("acknowledged", True), "index": index}
    except Exception as e:
        logger.error("update_settings_failed", index=index, error=str(e))
        raise


async def rename_index_via_reindex(
    client: Any,
    full_source: str,
    full_target: str,
    source: str,
    target: str,
) -> bool:
    """Rename an index using the reindex API, then delete the source.

    Elasticsearch doesn't have a direct rename, but we can use
    the reindex API to copy from source to target, then delete source.

    Raises:
        Exception: Re-raised from the transport after logging.
    """
    try:
        # Use reindex API to copy documents
        await client.reindex(
            {
                "source": {"index": full_source},
                "dest": {"index": full_target},
            },
            wait_for_completion=True,
        )

        # Delete the source index
        await client.indices.delete(index=full_source)

        return True
    except Exception as e:
        logger.error(
            "rename_index_failed",
            source=source,
            target=target,
            error=str(e),
        )
        raise


def build_bulk_delete_operations(
    full_index: str,
    document_ids: list[str],
) -> list[dict[str, Any]]:
    """Build ES bulk delete operation pairs for the given document IDs."""
    operations = []
    for doc_id in document_ids:
        operations.append({"delete": {"_index": full_index, "_id": doc_id}})
    return operations


def parse_bulk_delete_response(
    response: dict[str, Any],
    total: int,
) -> dict[str, Any]:
    """Parse a bulk delete response into success/failure counts."""
    # Parse response to count successes/failures
    successful = 0
    failed = 0
    errors: list[dict[str, Any]] = []

    for item in response.get("items", []):
        if "delete" in item:
            delete_result = item["delete"]
            if delete_result.get("status") in (200, 404):
                # 200 = deleted, 404 = not found (still considered success)
                successful += 1
            else:
                failed += 1
                errors.append(delete_result.get("error", {}))

    return {
        "successful": successful,
        "failed": failed,
        "total": total,
        "errors": errors if errors else None,
    }
