"""Unit tests for DatabaseSearchBase."""

import pytest

from lexigram.search.backends.base.database import DatabaseSearchBase, AsyncDatabaseSearchBase
from lexigram.search.backends.base.database import (
    AsyncDatabaseSearchBase as DBBaseModule,
)


class ConcreteDatabaseSearchBase(DatabaseSearchBase):
    """Concrete implementation for testing."""
    
    async def connect(self) -> None:
        pass
    
    async def close(self) -> None:
        pass
    
    async def _get_client(self):
        return None


class TestDatabaseSearchBase:
    """Test DatabaseSearchBase functionality."""

    @pytest.fixture
    def backend(self):
        """Create a concrete backend for testing."""
        return ConcreteDatabaseSearchBase()

    def test_extract_searchable_text_priority_fields(self, backend):
        """Test that priority fields are extracted first."""
        doc = {
            "id": "1",
            "title": "Important Title",
            "description": "Description here",
            "content": "Content here",
            "body": "Body text",
            "name": "Name value",
        }
        
        text = backend._extract_searchable_text(doc)
        
        # Priority fields should be included
        assert "Important Title" in text
        assert "Description here" in text
        assert "Content here" in text

    def test_extract_searchable_text_other_fields(self, backend):
        """Test that other string fields are included."""
        doc = {
            "id": "1",
            "custom_field": "Custom value",
            "another_field": "Another value",
        }
        
        text = backend._extract_searchable_text(doc)
        
        assert "Custom value" in text
        assert "Another value" in text

    def test_extract_searchable_text_excludes_long_strings(self, backend):
        """Test that very long strings are excluded."""
        long_string = "x" * 300  # Over 200 chars
        
        doc = {
            "id": "1",
            "title": "Short",
            "long_field": long_string,
        }
        
        text = backend._extract_searchable_text(doc)
        
        assert "Short" in text
        assert long_string not in text

    def test_extract_doc_id(self, backend):
        """Test document ID extraction."""
        # Test with 'id'
        doc = {"id": "doc1", "title": "Test"}
        assert backend._extract_doc_id(doc) == "doc1"
        
        # Test with '_id'
        doc = {"_id": "doc2", "title": "Test"}
        assert backend._extract_doc_id(doc) == "doc2"
        
        # Test with neither - should raise
        doc = {"title": "Test"}
        with pytest.raises(ValueError, match="must have an 'id'"):
            backend._extract_doc_id(doc)

    def test_sanitize_index_name(self, backend):
        """Test index name sanitization."""
        # Test hyphen replacement
        assert backend._sanitize_index_name("my-index") == "my_index"
        
        # Test dot replacement
        assert backend._sanitize_index_name("my.index") == "my_index"
        
        # Test space replacement
        assert backend._sanitize_index_name("my index") == "my_index"
        
        # Test combined
        assert backend._sanitize_index_name("my-index.test name") == "my_index_test_name"

    def test_prepare_document(self, backend):
        """Test document preparation adds searchable text."""
        doc = {"id": "1", "title": "Test Title", "content": "Test Content"}
        
        prepared = backend._prepare_document(doc)
        
        assert "_searchable" in prepared
        assert "Test Title" in prepared["_searchable"]
        assert "Test Content" in prepared["_searchable"]

    def test_prepare_document_preserves_existing(self, backend):
        """Test that existing _searchable field is preserved."""
        doc = {
            "id": "1", 
            "title": "Test Title",
            "_searchable": "custom searchable text"
        }
        
        prepared = backend._prepare_document(doc)
        
        # Should preserve custom searchable text
        assert prepared["_searchable"] == "custom searchable text"


class TestAsyncDatabaseSearchBase:
    """Test AsyncDatabaseSearchBase functionality."""

    @pytest.mark.asyncio
    async def test_build_filter_clause(self):
        """Test filter clause building."""
        # We need a concrete class to test this
        class TestBackend(AsyncDatabaseSearchBase):
            async def connect(self): pass
            async def close(self): pass
            async def _get_client(self): return None
            async def _get_pool(self): return None
        
        backend = TestBackend()
        
        # Test simple filter
        filters = {"category": "tech"}
        clause, params = await backend._build_filter_clause(filters)
        
        assert "document->>'category'" in clause
        assert "tech" in params
        
        # Test multiple filters
        filters = {"category": "tech", "status": "active"}
        clause, params = await backend._build_filter_clause(filters)
        
        assert "category" in clause
        assert "status" in clause

    @pytest.mark.asyncio
    async def test_build_filter_clause_rejects_injection_keys(self):
        """Filter keys are validated before JSON-path interpolation."""
        class TestBackend(AsyncDatabaseSearchBase):
            async def connect(self): pass
            async def close(self): pass
            async def _get_client(self): return None
            async def _get_pool(self): return None

        backend = TestBackend()

        for bad in ("cat' OR 1=1 --", "cat\" OR 1=1", "cat; DROP", "has space"):
            with pytest.raises(ValueError, match="Invalid filter field"):
                await backend._build_filter_clause({bad: "x"})

    def test_sanitize_index_name_blocks_breakout_characters(self):
        """Index names cannot break out of the table-name context."""
        backend = ConcreteDatabaseSearchBase()
        assert backend._sanitize_index_name("a; DROP TABLE t; --") == "a__DROP_TABLE_t____"
        assert backend._sanitize_index_name("x' OR '1'='1") == "x__OR__1___1"
        assert backend._sanitize_index_name("my-index.v1") == "my_index_v1"
