from __future__ import annotations

import hashlib
from typing import Any

from lexigram.serialization import dumps


class CacheKeyBuilder:
    """Builds consistent cache keys for different RAG components."""

    @staticmethod
    def build_embedding_key(text: str, model: str, prefix: str = "rag:") -> str:
        """Build cache key for embeddings."""
        data = dumps({"text": text, "model": model}, sort_keys=True)
        hash_val = hashlib.sha256(data).hexdigest()[:16]
        return f"{prefix}embedding:{hash_val}"

    @staticmethod
    def build_retrieval_key(
        query: str,
        params: dict[str, Any] | None = None,
        prefix: str = "rag:",
    ) -> str:
        """Build cache key for retrieval results."""
        params = params or {}
        sorted_params = {k: params[k] for k in sorted(params.keys())}
        data = dumps({"query": query, "params": sorted_params}, sort_keys=True)
        hash_val = hashlib.sha256(data).hexdigest()[:16]
        return f"{prefix}retrieval:{hash_val}"

    @staticmethod
    def build_document_key(
        doc_id: str,
        config: dict[str, Any] | None = None,
        prefix: str = "rag:",
    ) -> str:
        """Build cache key for preprocessed documents."""
        config = config or {}
        sorted_config = {k: config[k] for k in sorted(config.keys())}
        data = dumps({"doc_id": doc_id, "config": sorted_config}, sort_keys=True)
        hash_val = hashlib.sha256(data).hexdigest()[:16]
        return f"{prefix}document:{hash_val}"

    @staticmethod
    def build_reranking_key(
        query: str,
        document_ids: list[str],
        model: str,
        prefix: str = "rag:",
    ) -> str:
        """Build cache key for reranking results."""
        data = dumps(
            {
                "query": query,
                "document_ids": sorted(document_ids),
                "model": model,
            },
            sort_keys=True,
        )
        hash_val = hashlib.sha256(data).hexdigest()[:16]
        return f"{prefix}reranking:{hash_val}"

    @staticmethod
    def build_query_transformation_key(
        query: str,
        transformation_type: str,
        params: dict[str, Any] | None = None,
        prefix: str = "rag:",
    ) -> str:
        """Build cache key for query transformations."""
        params = params or {}
        sorted_params = {k: params[k] for k in sorted(params.keys())}
        data = dumps(
            {
                "query": query,
                "type": transformation_type,
                "params": sorted_params,
            },
            sort_keys=True,
        )
        hash_val = hashlib.sha256(data).hexdigest()[:16]
        return f"{prefix}query_transform:{hash_val}"
