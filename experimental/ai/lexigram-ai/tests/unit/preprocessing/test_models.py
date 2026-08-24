"""Tests for preprocessing data models."""

import pytest

try:
    from lexigram.ai.rag.preprocessing import (
        DocumentMetadata,
        DocumentType,
        ExtractedTable,
        PreprocessedDocument,
    )
except ImportError as e:
    pytest.skip(
        f"Skipping tests in module because importing preprocessing failed: {e}",
        allow_module_level=True,
    )


class TestExtractedTable:
    """Tests for ExtractedTable."""

    def test_creation(self):
        """Test table creation."""
        table = ExtractedTable(
            table_id="table_1",
            page_number=1,
            headers=["Name", "Age"],
            rows=[["Alice", "30"], ["Bob", "25"]],
        )

        assert table.table_id == "table_1"
        assert table.page_number == 1
        assert len(table.headers) == 2
        assert len(table.rows) == 2

    def test_to_markdown(self):
        """Test Markdown conversion."""
        table = ExtractedTable(
            table_id="table_1",
            page_number=1,
            headers=["Name", "Age"],
            rows=[["Alice", "30"], ["Bob", "25"]],
            caption="User Data",
        )

        markdown = table.to_markdown()

        assert "**User Data**" in markdown
        assert "| Name | Age |" in markdown
        assert "|---|---|" in markdown
        assert "| Alice | 30 |" in markdown
        assert "| Bob | 25 |" in markdown

    def test_to_csv(self):
        """Test CSV conversion."""
        table = ExtractedTable(
            table_id="table_1",
            page_number=1,
            headers=["Name", "Age"],
            rows=[["Alice", "30"], ["Bob", "25"]],
        )

        csv = table.to_csv()

        assert "Name,Age" in csv
        assert "Alice,30" in csv
        assert "Bob,25" in csv

    def test_to_json(self):
        """Test JSON conversion."""
        table = ExtractedTable(
            table_id="table_1",
            page_number=1,
            headers=["Name", "Age"],
            rows=[["Alice", "30"], ["Bob", "25"]],
        )

        json_data = table.to_json()

        assert len(json_data) == 2
        assert json_data[0]["Name"] == "Alice"
        assert json_data[0]["Age"] == "30"
        assert json_data[1]["Name"] == "Bob"
        assert json_data[1]["Age"] == "25"

    def test_to_json_without_headers(self):
        """Test JSON conversion without headers."""
        table = ExtractedTable(
            table_id="table_1",
            page_number=1,
            rows=[["value1", "value2"], ["value3", "value4"]],
        )

        json_data = table.to_json()

        assert len(json_data) == 2
        assert json_data[0]["row"] == 0
        assert json_data[0]["data"] == ["value1", "value2"]


class TestDocumentMetadata:
    """Tests for DocumentMetadata."""

    def test_creation(self):
        """Test metadata creation."""
        metadata = DocumentMetadata(
            title="Test Document",
            author="Test Author",
            language="en",
            word_count=100,
            keywords=["test", "document"],
        )

        assert metadata.title == "Test Document"
        assert metadata.author == "Test Author"
        assert metadata.language == "en"
        assert metadata.word_count == 100
        assert len(metadata.keywords) == 2

    def test_default_values(self):
        """Test default values."""
        metadata = DocumentMetadata()

        assert metadata.title is None
        assert metadata.keywords == []
        assert metadata.custom == {}
        assert metadata.document_type == DocumentType.UNKNOWN


class TestPreprocessedDocument:
    """Tests for PreprocessedDocument."""

    def test_creation(self):
        """Test document creation."""
        metadata = DocumentMetadata(title="Test")

        doc = PreprocessedDocument(
            text="Test content",
            metadata=metadata,
            images=[],
            tables=[],
        )

        assert doc.text == "Test content"
        assert doc.metadata.title == "Test"
        assert len(doc.images) == 0
        assert len(doc.tables) == 0
        assert doc.timestamp is not None
