"""Tests for graph backends."""

from __future__ import annotations

import pytest

from lexigram.graph.backends.memory import backend, graph as mem_graph


class TestInMemoryGraphStore:
    """Tests for InMemoryGraphStore."""

    @pytest.fixture
    def store(self) -> backend.InMemoryGraphStore:
        """Create a fresh store."""
        return backend.InMemoryGraphStore()

    @pytest.mark.asyncio
    async def test_connect_noop(self, store: backend.InMemoryGraphStore) -> None:
        """Verify connect is a no-op."""
        await store.connect()

    @pytest.mark.asyncio
    async def test_disconnect_clears_graphs(self, store: backend.InMemoryGraphStore) -> None:
        """Verify disconnect clears graphs."""
        gra = await store.get_graph("test")
        await store.disconnect()
        graphs = await store.list_graphs()
        assert len(graphs) == 0

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(
        self, store: backend.InMemoryGraphStore
    ) -> None:
        """Verify health check returns healthy."""
        result = await store.health_check()
        assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_get_graph_creates_new(
        self, store: backend.InMemoryGraphStore
    ) -> None:
        """Verify get_graph creates new graph."""
        gra = await store.get_graph("mygraph")
        assert isinstance(gra, mem_graph.InMemoryGraph)

    @pytest.mark.asyncio
    async def test_get_graph_returns_existing(
        self, store: backend.InMemoryGraphStore
    ) -> None:
        """Verify get_graph returns existing graph."""
        gra1 = await store.get_graph("mygraph")
        gra2 = await store.get_graph("mygraph")
        assert gra1 is gra2

    @pytest.mark.asyncio
    async def test_get_graph_default_name(
        self, store: backend.InMemoryGraphStore
    ) -> None:
        """Verify default graph name works."""
        gra = await store.get_graph()
        assert gra.name == "default"

    @pytest.mark.asyncio
    async def test_list_graphs_returns_all(
        self, store: backend.InMemoryGraphStore
    ) -> None:
        """Verify list_graphs returns all graphs."""
        await store.get_graph("a")
        await store.get_graph("b")
        graphs = await store.list_graphs()
        assert len(graphs) == 2
        names = [g.name for g in graphs]
        assert "a" in names
        assert "b" in names

    @pytest.mark.asyncio
    async def test_list_graphs_empty(
        self, store: backend.InMemoryGraphStore
    ) -> None:
        """Verify list_graphs returns empty list initially."""
        graphs = await store.list_graphs()
        assert graphs == []