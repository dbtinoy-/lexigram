"""Tests for search functionality."""

import pytest
import lexigram.testing.clients.search.client as search_client_module

from lexigram.search import (
    SearchResponse,
    SearchResult,
)
search_client_module.SearchResult = SearchResult

from lexigram.testing.clients.search import (
    MockSearchBackend,
    SearchTestBed,
    SearchTestClient,
    SearchTestData,
)


class TestSearchTestData:
    """Test the SearchTestData class."""

    def test_sample_searchable_documents(self):
        """Test sample searchable documents."""
        docs = SearchTestData.sample_searchable_documents()
        assert len(docs) == 3
        assert all("id" in doc for doc in docs)
        assert all("title" in doc for doc in docs)
        assert all("content" in doc for doc in docs)

    def test_sample_search_queries(self):
        """Test sample search queries."""
        queries = SearchTestData.sample_search_queries()
        assert len(queries) == 4
        assert all("query" in q for q in queries)
        assert all("filters" in q for q in queries)
        assert all("expected_results" in q for q in queries)

    def test_sample_search_results(self):
        """Test sample search results."""
        results = SearchTestData.sample_search_results()
        assert len(results) == 2
        assert all("document" in r for r in results)
        assert all("score" in r for r in results)
        assert all("highlights" in r for r in results)

    def test_sample_index_configs(self):
        """Test sample index configurations."""
        configs = SearchTestData.sample_index_configs()
        assert len(configs) == 2
        assert all("name" in c for c in configs)
        assert all("settings" in c for c in configs)
        assert all("mappings" in c for c in configs)


class TestMockSearchBackend:
    """Test the MockSearchBackend class."""

    @pytest.fixture
    def mock_backend(self) -> MockSearchBackend:
        """Create a mock backend instance."""
        return MockSearchBackend()

    @pytest.mark.asyncio
    async def test_create_index(self, mock_backend: MockSearchBackend):
        """Test index creation."""
        config = {"settings": {"replicas": 1}}
        await mock_backend.create_index("test_index", config)
        assert "test_index" in mock_backend.indices
        assert mock_backend.indices["test_index"] == config

    @pytest.mark.asyncio
    async def test_delete_index(self, mock_backend: MockSearchBackend):
        """Test index deletion."""
        await mock_backend.create_index("test_index", {})
        assert "test_index" in mock_backend.indices

        await mock_backend.delete_index("test_index")
        assert "test_index" not in mock_backend.indices

    @pytest.mark.asyncio
    async def test_index_exists(self, mock_backend: MockSearchBackend):
        """Test index existence check."""
        assert not await mock_backend.index_exists("test_index")

        await mock_backend.create_index("test_index", {})
        assert await mock_backend.index_exists("test_index")

    @pytest.mark.asyncio
    async def test_index_document(self, mock_backend: MockSearchBackend):
        """Test document indexing."""
        doc = {"id": "doc1", "title": "Test Document"}
        await mock_backend.index_document("test_index", "doc1", doc)

        assert "test_index" in mock_backend.documents
        assert "doc1" in mock_backend.documents["test_index"]
        assert mock_backend.documents["test_index"]["doc1"] == doc

    @pytest.mark.asyncio
    async def test_delete_document(self, mock_backend: MockSearchBackend):
        """Test document deletion."""
        doc = {"id": "doc1", "title": "Test Document"}
        await mock_backend.index_document("test_index", "doc1", doc)
        assert "doc1" in mock_backend.documents["test_index"]

        await mock_backend.delete_document("test_index", "doc1")
        assert "doc1" not in mock_backend.documents["test_index"]

    @pytest.mark.asyncio
    async def test_search_basic(self, mock_backend: MockSearchBackend):
        """Test basic search functionality."""
        # Index some documents
        docs = SearchTestData.sample_searchable_documents()
        for doc in docs:
            await mock_backend.index_document("test_index", doc["id"], doc)

        # Search for "python"
        results = await mock_backend.search("test_index", "python")
        assert results["total"] >= 1
        assert len(results["results"]) >= 1
        assert "python" in results["query"].lower()

    @pytest.mark.asyncio
    async def test_search_with_filters(self, mock_backend: MockSearchBackend):
        """Test search with filters."""
        docs = SearchTestData.sample_searchable_documents()
        for doc in docs:
            await mock_backend.index_document("test_index", doc["id"], doc)

        # Search with category filter
        results = await mock_backend.search(
            "test_index", "programming", filters={"category": "education"},
        )
        assert results["total"] >= 1
        # Verify filters were recorded
        calls = mock_backend.get_search_calls()
        assert len(calls) >= 1
        assert calls[-1]["filters"]["category"] == "education"

    @pytest.mark.asyncio
    async def test_get_document(self, mock_backend: MockSearchBackend):
        """Test document retrieval."""
        doc = {"id": "doc1", "title": "Test Document"}
        await mock_backend.index_document("test_index", "doc1", doc)

        retrieved = await mock_backend.get_document("test_index", "doc1")
        assert retrieved == doc

        # Test non-existent document
        retrieved = await mock_backend.get_document("test_index", "nonexistent")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_bulk_index(self, mock_backend: MockSearchBackend):
        """Test bulk indexing."""
        docs = SearchTestData.sample_searchable_documents()
        await mock_backend.bulk_index("test_index", docs)

        assert "test_index" in mock_backend.documents
        assert len(mock_backend.documents["test_index"]) == len(docs)

    @pytest.mark.asyncio
    async def test_health_check(self, mock_backend: MockSearchBackend):
        """Test health check."""
        health = await mock_backend.health_check()
        assert health.status.value == "healthy"
        assert health.details["backend"] == "mock"


class TestSearchTestBed:
    """Test the SearchTestBed class."""

    @pytest.mark.asyncio
    async def test_setup_teardown(self):
        """Test setup and teardown."""
        test_bed = SearchTestBed()
        await test_bed.setup()

        # Setup should populate test data
        docs = test_bed.get_indexed_documents()
        assert len(docs) == 3  # From sample data

        # After teardown, should be empty
        await test_bed.teardown()
        docs = test_bed.get_indexed_documents()
        assert len(docs) == 0

    @pytest.mark.asyncio
    async def test_simulate_document_indexing(self):
        """Test document indexing simulation."""
        test_bed = SearchTestBed()
        await test_bed.setup()

        doc = {"id": "test_doc", "title": "Test Title"}
        await test_bed.simulate_document_indexing("test_index", doc)

        indexed = test_bed.get_indexed_documents()
        assert len(indexed) == 4  # 3 from setup + 1 new
        assert indexed[-1] == doc

        await test_bed.teardown()

    @pytest.mark.asyncio
    async def test_simulate_search_operation(self):
        """Test search operation simulation."""
        test_bed = SearchTestBed()
        await test_bed.setup()

        await test_bed.simulate_search_operation(
            "test_index",
            "test query",
            {"category": "test"},
            [{"document": {"id": "doc1"}, "score": 0.9}],
        )

        operations = test_bed.get_search_operations()
        assert len(operations) == 1
        assert operations[0]["query"] == "test query"
        assert operations[0]["filters"]["category"] == "test"

        await test_bed.teardown()


class TestSearchTestClient:
    """Test the SearchTestClient class."""

    @pytest.mark.asyncio
    async def test_start_provider(self):
        """Test provider startup."""
        test_bed = SearchTestBed()
        await test_bed.setup()
        client = SearchTestClient(test_bed)

        provider = await client.start_provider()
        assert provider is not None
        assert isinstance(provider, MockSearchBackend)

        await client.stop_provider()
        await test_bed.teardown()

    @pytest.mark.asyncio
    async def test_stop_provider(self):
        """Test provider shutdown."""
        test_bed = SearchTestBed()
        await test_bed.setup()
        client = SearchTestClient(test_bed)

        await client.start_provider()
        assert client.backend is not None

        await client.stop_provider()
        await test_bed.teardown()

    @pytest.mark.asyncio
    async def test_create_search_engine(self):
        """Test search engine creation."""
        test_bed = SearchTestBed()
        await test_bed.setup()
        client = SearchTestClient(test_bed)

        engine = await client.create_search_engine()
        assert engine is not None
        assert isinstance(engine, MockSearchBackend)

        await client.stop_provider()
        await test_bed.teardown()

    @pytest.mark.asyncio
    async def test_index_test_documents(self):
        """Test indexing test documents."""
        test_bed = SearchTestBed()
        await test_bed.setup()
        client = SearchTestClient(test_bed)

        await client.start_provider()
        await client.index_test_documents()

        # Check that documents were indexed in test bed
        indexed = client.test_bed.get_indexed_documents()
        assert len(indexed) >= 3  # At least the sample documents

        await client.stop_provider()
        await test_bed.teardown()

    @pytest.mark.asyncio
    async def test_perform_test_search(self):
        """Test performing test search."""
        test_bed = SearchTestBed()
        await test_bed.setup()
        client = SearchTestClient(test_bed)

        await client.start_provider()
        await client.index_test_documents()

        response = await client.perform_test_search("python")
        assert isinstance(response, SearchResponse)
        assert hasattr(response, "results")
        assert hasattr(response, "total")

        await client.stop_provider()
        await test_bed.teardown()

    @pytest.mark.asyncio
    async def test_verify_search_results(self):
        """Test search result verification."""
        test_bed = SearchTestBed()
        await test_bed.setup()
        client = SearchTestClient(test_bed)

        await client.start_provider()
        await client.index_test_documents()

        # Test with expected results
        verified = await client.verify_search_results("python programming", ["doc_1"])
        assert isinstance(verified, bool)

        await client.stop_provider()
        await test_bed.teardown()

    @pytest.mark.asyncio
    async def test_search_context(self):
        """Test search context manager."""
        test_bed = SearchTestBed()
        await test_bed.setup()
        client = SearchTestClient(test_bed)

        async with client.search_context() as backend:
            assert backend is not None
            assert isinstance(backend, MockSearchBackend)

        await test_bed.teardown()


class TestSearchIntegration:
    """Integration tests for search functionality."""

    @pytest.mark.asyncio
    async def test_full_search_workflow(self):
        """Test complete search workflow."""
        test_bed = SearchTestBed()
        await test_bed.setup()
        client = SearchTestClient(test_bed)

        # Start provider and index documents
        await client.start_provider()
        await client.index_test_documents()

        # Perform search
        response = await client.perform_test_search(
            "python", filters={"category": "education"},
        )

        # Verify response structure
        assert isinstance(response, SearchResponse)
        assert hasattr(response, "results")
        assert hasattr(response, "total")

        # Check that search operation was recorded
        operations = client.test_bed.get_search_operations()
        assert len(operations) >= 1

        await client.stop_provider()
        await test_bed.teardown()

    @pytest.mark.asyncio
    async def test_multiple_search_queries(self):
        """Test multiple search queries."""
        test_bed = SearchTestBed()
        await test_bed.setup()
        client = SearchTestClient(test_bed)

        await client.start_provider()
        await client.index_test_documents()

        queries = SearchTestData.sample_search_queries()
        for query_data in queries:
            response = await client.perform_test_search(
                query_data["query"], filters=query_data["filters"],
            )
            assert isinstance(response, SearchResponse)

        await client.stop_provider()
        await test_bed.teardown()

    @pytest.mark.asyncio
    async def test_search_engine_integration(self):
        """Test search engine integration."""
        test_bed = SearchTestBed()
        await test_bed.setup()
        client = SearchTestClient(test_bed)

        engine = await client.create_search_engine()

        # Index documents
        await client.index_test_documents()

        # Perform search through engine
        response = await engine.search("test_index", "python")
        assert isinstance(response, dict)  # Mock backend returns dict
        assert "results" in response

        await client.stop_provider()
        await test_bed.teardown()
