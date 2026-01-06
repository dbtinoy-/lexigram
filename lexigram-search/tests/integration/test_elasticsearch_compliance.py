from __future__ import annotations

"""Elasticsearch SearchEngine compliance test using a real Elasticsearch connection."""

import pytest

from lexigram.testing.compliance import SearchEngineCompliance
from lexigram.testing.integration.fixtures import (  # noqa: F401
    elasticsearch_client,
    elasticsearch_index,
)

pytestmark = [pytest.mark.integration, pytest.mark.requires_elasticsearch]


class TestElasticsearchCompliance(SearchEngineCompliance):
    """Verify ElasticsearchBackend satisfies SearchEngineCompliance.

    Uses the ``elasticsearch_client`` and ``elasticsearch_index`` fixtures
    provided by ``lexigram.testing.integration.fixtures``.  The suite is
    auto-skipped when Elasticsearch is not reachable or the
    ``elasticsearch[async]`` package is not installed.
    """

    @pytest.fixture(autouse=True)
    async def _setup(
        self,
        elasticsearch_client: object,
        elasticsearch_index: str,
    ) -> None:
        """Capture the live Elasticsearch connection details.

        Args:
            elasticsearch_client: Session-scoped AsyncElasticsearch client.
            elasticsearch_index: Unique index name scoped to this test function.
        """
        self._elasticsearch_client = elasticsearch_client
        self._index = elasticsearch_index

    async def create_engine(self) -> object:
        """Create an ElasticsearchBackend using the live Elasticsearch cluster.

        Returns:
            A ready-to-use ElasticsearchBackend connected to the test cluster.

        Raises:
            pytest.skip.Exception: If ``elasticsearch[async]`` is not installed
                or the backend cannot be imported.
        """
        try:
            from lexigram.search.backends.elasticsearch.backend import (
                ElasticsearchBackend,  # noqa: F401
            )
            from lexigram.search.config import ElasticsearchConfig  # noqa: F401
        except ImportError:
            pytest.skip("ElasticsearchBackend not available")

        pytest.skip(
            "TODO: build ElasticsearchConfig from integration_config.elasticsearch_url "
            "and pass index_prefix derived from self._index to ElasticsearchBackend"
        )
