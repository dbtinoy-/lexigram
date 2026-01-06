from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.core.health import HealthStatus
from lexigram.graph.config import Neo4jConfig
from lexigram.graph.backends.memory.backend import InMemoryGraphStore
from lexigram.graph.backends.neo4j.backend import Neo4jGraphStore


class TestNeo4jGraphStore:
    @pytest.fixture
    def config(self) -> Neo4jConfig:
        return Neo4jConfig(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password",
        )

    @pytest.fixture
    def store(self, config: Neo4jConfig) -> Neo4jGraphStore:
        return Neo4jGraphStore(config)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="neo4j package not available in test environment")
    async def test_connect_creates_driver(self, store: Neo4jGraphStore) -> None:
        pass

    @pytest.mark.asyncio
    async def test_disconnect_closes_driver(self, store: Neo4jGraphStore) -> None:
        mock_driver = AsyncMock()
        store._driver = mock_driver
        await store.disconnect()
        mock_driver.close.assert_awaited_once()
        assert store._driver is None

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_when_connected(
        self, store: Neo4jGraphStore
    ) -> None:
        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock()
        store._driver = mock_driver
        result = await store.health_check()
        assert result.status == HealthStatus.HEALTHY
        assert result.component == "graph.neo4j"

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_when_not_connected(
        self, store: Neo4jGraphStore
    ) -> None:
        result = await store.health_check()
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_query_returns_list_of_dicts(self, store: Neo4jGraphStore) -> None:
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[{"name": "test"}])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)
        store._driver = mock_driver
        result = await store.query("MATCH (n) RETURN n")
        assert result == [{"name": "test"}]

    @pytest.mark.asyncio
    async def test_list_graphs_parses_result(self, store: Neo4jGraphStore) -> None:
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[{"name": "neo4j"}])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)
        store._driver = mock_driver
        result = await store.list_graphs()
        assert len(result) == 1
        assert result[0].name == "neo4j"

    @pytest.mark.asyncio
    async def test_get_graph_returns_neo4j_graph(self, store: Neo4jGraphStore) -> None:
        mock_driver = MagicMock()
        store._driver = mock_driver
        graph = await store.get_graph("testdb")
        assert graph._driver is mock_driver
        assert graph._database == "testdb"


class TestInMemoryGraphStore:
    @pytest.fixture
    def store(self) -> InMemoryGraphStore:
        return InMemoryGraphStore()

    @pytest.mark.asyncio
    async def test_connect_is_noop(self, store: InMemoryGraphStore) -> None:
        await store.connect()

    @pytest.mark.asyncio
    async def test_disconnect_clears_graphs(self, store: InMemoryGraphStore) -> None:
        await store.get_graph("test")
        await store.disconnect()
        graphs = await store.list_graphs()
        assert len(graphs) == 0

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(
        self, store: InMemoryGraphStore
    ) -> None:
        result = await store.health_check()
        assert result.status == HealthStatus.HEALTHY
        assert result.component == "graph.memory"

    @pytest.mark.asyncio
    async def test_query_not_supported(self, store: InMemoryGraphStore) -> None:
        await store.connect()
        graph = await store.get_graph("default")
        with pytest.raises(NotImplementedError):
            await graph.query("MATCH (n) RETURN n")

    @pytest.mark.asyncio
    async def test_get_graph_creates_new_graph(self, store: InMemoryGraphStore) -> None:
        graph = await store.get_graph("test")
        assert graph._name == "test"

    @pytest.mark.asyncio
    async def test_get_graph_returns_existing_graph(
        self, store: InMemoryGraphStore
    ) -> None:
        graph1 = await store.get_graph("test")
        graph2 = await store.get_graph("test")
        assert graph1 is graph2

    @pytest.mark.asyncio
    async def test_list_graphs_returns_all_graph_names(
        self, store: InMemoryGraphStore
    ) -> None:
        await store.get_graph("graph1")
        await store.get_graph("graph2")
        graphs = await store.list_graphs()
        assert len(graphs) == 2
        names = [g.name for g in graphs]
        assert "graph1" in names
        assert "graph2" in names
