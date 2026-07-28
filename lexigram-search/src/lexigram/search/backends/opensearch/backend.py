"""OpenSearch backend — OpenSearch-compatible extension of ElasticsearchBackend."""

from __future__ import annotations

from typing import Any

from lexigram.search.backends.elasticsearch import ElasticsearchBackend
from lexigram.search.config import ElasticsearchConfig, OpenSearchConfig


class OpenSearchBackend(ElasticsearchBackend):
    """OpenSearch backend — a drop-in replacement for ElasticsearchBackend.

    Uses the ``opensearch-py`` SDK (``AsyncOpenSearch``) instead of the
    official ``elasticsearch-py`` client.  All query, index-management, and
    bulk-operation logic is inherited from :class:`ElasticsearchBackend`; only
    client construction differs.

    Args:
        config: OpenSearch connection configuration.  Accepts an
            :class:`~lexigram.search.config.OpenSearchConfig` instance, a plain
            ``dict`` of the same fields, or ``None`` for all defaults.

    Example:
        ::

            from lexigram.search.backends.opensearch import OpenSearchBackend
            from lexigram.search.config import OpenSearchConfig

            backend = OpenSearchBackend(
                OpenSearchConfig(hosts=["https://search:9200"], use_ssl=True)
            )
    """

    def __init__(self, config: OpenSearchConfig | dict[str, Any] | None = None) -> None:
        if isinstance(config, dict):
            config = OpenSearchConfig(**config)
        elif config is None:
            config = OpenSearchConfig()

        # Build a minimal ElasticsearchConfig that satisfies the attribute
        # references used by the inherited _get_index_name, _ensure_index, and
        # health_check methods (which all read self.es_config).  _get_client is
        # fully overridden here so es_compat never reaches the ES SDK.
        es_compat = ElasticsearchConfig(
            hosts=config.hosts,
            index_prefix=config.index_prefix,
            use_ssl=config.use_ssl,
            verify_certs=config.verify_ssl,
        )
        super().__init__(es_compat)

        # Store the OpenSearch-native config for _get_client.
        self.os_config = config

    async def _get_client(self) -> Any:
        """Get or create the AsyncOpenSearch client.

        Returns:
            A ready ``AsyncOpenSearch`` client instance.
        """
        if self._client is None:
            from opensearchpy import AsyncOpenSearch  # type: ignore[import-not-found]

            kwargs: dict[str, Any] = {"hosts": self.os_config.hosts}

            if self.os_config.username and self.os_config.password:
                kwargs["http_auth"] = (self.os_config.username, self.os_config.password)

            if self.os_config.use_ssl:
                kwargs["use_ssl"] = True
                kwargs["verify_certs"] = self.os_config.verify_ssl

            self._client = AsyncOpenSearch(**kwargs)

        return self._client


__all__ = ["OpenSearchBackend"]
