"""Minimal tests for search functionality."""

import pytest
import lexigram.testing.clients.search.client as search_client_module

from lexigram.search import SearchResult
search_client_module.SearchResult = SearchResult

from lexigram.testing.clients.search import (
    MockSearchBackend,
    SearchTestBed,
    SearchTestClient,
    SearchTestData,
)


@pytest.mark.asyncio
async def test_search_test_data():
    """Test SearchTestData provides sample data."""
    docs = SearchTestData.sample_searchable_documents()
    assert len(docs) == 3
    assert all("id" in doc for doc in docs)

    queries = SearchTestData.sample_search_queries()
    assert len(queries) == 4
    assert all("query" in q for q in queries)


@pytest.mark.asyncio
async def test_mock_backend_basic_operations():
    """Test MockSearchBackend basic operations."""
    backend = MockSearchBackend()

    # Test index operations
    await backend.create_index("test_index", {})
    assert await backend.index_exists("test_index")

    # Test document operations
    doc = {"id": "doc1", "title": "Test"}
    await backend.index_document("test_index", "doc1", doc)
    retrieved = await backend.get_document("test_index", "doc1")
    assert retrieved == doc

    # Test search
    results = await backend.search("test_index", "test")
    assert "results" in results
    assert "total" in results


@pytest.mark.asyncio
async def test_search_test_bed_setup():
    """Test SearchTestBed setup and teardown."""
    test_bed = SearchTestBed()
    await test_bed.setup()

    # Should have sample documents
    docs = test_bed.get_indexed_documents()
    assert len(docs) == 3

    await test_bed.teardown()

    # Should be empty after teardown
    docs = test_bed.get_indexed_documents()
    assert len(docs) == 0


@pytest.mark.asyncio
async def test_search_test_client_provider():
    """Test SearchTestClient provider management."""
    test_bed = SearchTestBed()
    await test_bed.setup()
    client = SearchTestClient(test_bed)

    # Start provider
    backend = await client.start_provider()
    assert backend is not None
    assert isinstance(backend, MockSearchBackend)

    # Stop provider
    await client.stop_provider()


@pytest.mark.asyncio
async def test_search_test_client_context():
    """Test SearchTestClient context manager."""
    test_bed = SearchTestBed()
    await test_bed.setup()
    client = SearchTestClient(test_bed)

    async with client.search_context() as backend:
        assert backend is not None
        assert isinstance(backend, MockSearchBackend)


@pytest.mark.asyncio
async def test_search_test_client_indexing():
    """Test SearchTestClient document indexing."""
    test_bed = SearchTestBed()
    await test_bed.setup()
    client = SearchTestClient(test_bed)

    await client.start_provider()
    await client.index_test_documents()

    # Check documents were indexed
    indexed = client.test_bed.get_indexed_documents()
    assert len(indexed) >= 6  # 3 from setup + 3 from indexing

    await client.stop_provider()


@pytest.mark.asyncio
async def test_search_test_client_search():
    """Test SearchTestClient search operations."""
    test_bed = SearchTestBed()
    await test_bed.setup()
    client = SearchTestClient(test_bed)

    await client.start_provider()
    await client.index_test_documents()

    # Perform search
    response = await client.perform_test_search("python")
    assert hasattr(response, "results")
    assert hasattr(response, "total")

    # Check operation was recorded
    operations = client.test_bed.get_search_operations()
    assert len(operations) >= 1

    await client.stop_provider()
