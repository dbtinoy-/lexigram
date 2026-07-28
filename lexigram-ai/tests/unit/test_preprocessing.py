"""Tests for document preprocessing pipeline."""

import pytest

try:
    from lexigram.ai.rag.preprocessing import (
        DocumentMetadata,
        DocumentType,
        ExtractedTable,
        MetadataEnricher,
        OCRPreprocessor,
        PreprocessedDocument,
        PreprocessingPipeline,
        TableExtractor,
        preprocess_document,
    )
except ImportError as e:  # pragma: no cover - skip tests when module import fails in this environment
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


class TestOCRPreprocessor:
    """Tests for OCRPreprocessor."""

    @pytest.mark.asyncio
    async def test_basic_ocr(self):
        """Test basic OCR preprocessing."""
        preprocessor = OCRPreprocessor()

        with pytest.raises(NotImplementedError, match="OCR preprocessing is not natively implemented"):
            await preprocessor.preprocess("image_content")

    @pytest.mark.asyncio
    async def test_ocr_with_language(self):
        """Test OCR with language specification."""
        preprocessor = OCRPreprocessor(language="fra")

        with pytest.raises(NotImplementedError, match="OCR preprocessing is not natively implemented"):
            await preprocessor.preprocess("french_image")


class TestTableExtractor:
    """Tests for TableExtractor."""

    @pytest.mark.asyncio
    async def test_extract_markdown_table(self):
        """Test extracting Markdown table."""
        content = """
# Document

Some text here.

| Name | Age | City |
|------|-----|------|
| Alice | 30 | NYC |
| Bob | 25 | LA |

More text.
"""

        extractor = TableExtractor()
        result = await extractor.preprocess(content)

        assert len(result.tables) == 1
        table = result.tables[0]
        assert table.headers == ["Name", "Age", "City"]
        assert len(table.rows) == 2
        assert table.rows[0] == ["Alice", "30", "NYC"]
        assert table.rows[1] == ["Bob", "25", "LA"]

    @pytest.mark.asyncio
    async def test_extract_html_table(self):
        """Test extracting HTML table."""
        content = """
<html>
<body>
<table>
    <tr>
        <th>Product</th>
        <th>Price</th>
    </tr>
    <tr>
        <td>Widget</td>
        <td>$10</td>
    </tr>
    <tr>
        <td>Gadget</td>
        <td>$20</td>
    </tr>
</table>
</body>
</html>
"""

        extractor = TableExtractor()
        result = await extractor.preprocess(content)

        assert len(result.tables) == 1
        table = result.tables[0]
        assert table.headers == ["Product", "Price"]
        assert len(table.rows) == 2
        assert table.rows[0] == ["Widget", "$10"]

    @pytest.mark.asyncio
    async def test_no_tables(self):
        """Test content without tables."""
        content = "Just plain text without any tables."

        extractor = TableExtractor()
        result = await extractor.preprocess(content)

        assert len(result.tables) == 0
        assert result.text == content

    @pytest.mark.asyncio
    async def test_multiple_markdown_tables(self):
        """Test extracting multiple tables."""
        content = """
| Table 1 | Data |
|---------|------|
| A | 1 |

Some text.

| Table 2 | Info |
|---------|------|
| B | 2 |
"""

        extractor = TableExtractor()
        result = await extractor.preprocess(content)

        assert len(result.tables) == 2
        assert result.tables[0].headers == ["Table 1", "Data"]
        assert result.tables[1].headers == ["Table 2", "Info"]


class TestMetadataEnricher:
    """Tests for MetadataEnricher."""

    @pytest.mark.asyncio
    async def test_extract_title_from_markdown(self):
        """Test title extraction from Markdown."""
        content = """
# Main Title

This is the content of the document.
"""

        enricher = MetadataEnricher()
        result = await enricher.preprocess(content)

        assert result.metadata.title == "Main Title"

    @pytest.mark.asyncio
    async def test_extract_title_from_html(self):
        """Test title extraction from HTML."""
        content = """
<html>
<head><title>HTML Title</title></head>
<body>Content</body>
</html>
"""

        enricher = MetadataEnricher()
        result = await enricher.preprocess(content)

        assert result.metadata.title == "HTML Title"

    @pytest.mark.asyncio
    async def test_word_count(self):
        """Test word count calculation."""
        content = "This is a test document with ten words in total."

        enricher = MetadataEnricher()
        result = await enricher.preprocess(content)

        assert result.metadata.word_count == 10

    @pytest.mark.asyncio
    async def test_language_detection(self):
        """Test language detection."""
        # English content with common words
        content = "The quick brown fox jumps over the lazy dog. This is a test."

        enricher = MetadataEnricher()
        result = await enricher.preprocess(content)

        assert result.metadata.language == "en"

    @pytest.mark.asyncio
    async def test_keyword_extraction(self):
        """Test keyword extraction."""
        content = """
        Machine learning is a subset of artificial intelligence.
        Machine learning algorithms learn from data.
        Learning patterns from data is the key to machine learning.
        """

        enricher = MetadataEnricher()
        result = await enricher.preprocess(content)

        # "machine" and "learning" should be top keywords
        assert "machine" in result.metadata.keywords
        assert "learning" in result.metadata.keywords

    @pytest.mark.asyncio
    async def test_summary_generation(self):
        """Test summary generation."""
        content = (
            """
        This is the first sentence. This is the second sentence.
        This is the third sentence. This is the fourth sentence.
        """
            * 10
        )  # Make it long

        enricher = MetadataEnricher()
        result = await enricher.preprocess(content)

        assert result.metadata.summary is not None
        assert len(result.metadata.summary) > 0
        assert len(result.metadata.summary) <= 200  # Max length


class TestPreprocessingPipeline:
    """Tests for PreprocessingPipeline."""

    @pytest.mark.asyncio
    async def test_empty_pipeline(self):
        """Test empty pipeline."""
        pipeline = PreprocessingPipeline()

        result = await pipeline.preprocess("test content")

        assert result.text == "test content"
        assert result.processing_time is not None

    @pytest.mark.asyncio
    async def test_single_preprocessor(self):
        """Test pipeline with single preprocessor."""
        pipeline = PreprocessingPipeline()
        pipeline.add_preprocessor(MetadataEnricher())

        content = "# Test\n\nThis is test content."
        result = await pipeline.preprocess(content)

        assert result.metadata.title == "Test"
        assert result.metadata.word_count > 0

    @pytest.mark.asyncio
    async def test_multiple_preprocessors(self):
        """Test pipeline with multiple preprocessors."""
        pipeline = PreprocessingPipeline(
            [
                TableExtractor(),
                MetadataEnricher(),
            ],
        )

        content = """
# Document

| Name | Value |
|------|-------|
| A | 1 |

This is some content.
"""

        result = await pipeline.preprocess(content)

        # Table should be extracted
        assert len(result.tables) == 1

        # Metadata should be enriched
        assert result.metadata.title == "Document"
        assert result.metadata.word_count > 0

    @pytest.mark.asyncio
    async def test_processing_time(self):
        """Test processing time tracking."""
        pipeline = PreprocessingPipeline([MetadataEnricher()])

        result = await pipeline.preprocess("test content")

        assert result.processing_time is not None
        assert result.processing_time >= 0


class TestPreprocessDocumentFunction:
    """Tests for preprocess_document convenience function."""

    @pytest.mark.asyncio
    async def test_default_preprocessing(self):
        """Test default preprocessing."""
        content = """
# Test Document

| Col1 | Col2 |
|------|------|
| A | B |

Some content.
"""

        result = await preprocess_document(content)

        # Tables should be extracted
        assert len(result.tables) == 1

        # Metadata should be enriched
        assert result.metadata.title == "Test Document"
        assert result.metadata.word_count > 0

    @pytest.mark.asyncio
    async def test_disable_table_extraction(self):
        """Test disabling table extraction."""
        content = """
| Col1 | Col2 |
|------|------|
| A | B |
"""

        result = await preprocess_document(content, extract_tables=False)

        assert len(result.tables) == 0

    @pytest.mark.asyncio
    async def test_disable_metadata_enrichment(self):
        """Test disabling metadata enrichment."""
        content = "# Title\n\nContent"

        result = await preprocess_document(content, enrich_metadata=False)

        # Title should not be extracted
        assert result.metadata.title is None

    @pytest.mark.asyncio
    async def test_enable_ocr(self):
        """Test enabling OCR."""
        with pytest.raises(NotImplementedError, match="OCR preprocessing is not natively implemented"):
            await preprocess_document("image_data", ocr_enabled=True)


class TestIntegration:
    """Integration tests for complete preprocessing workflows."""

    @pytest.mark.asyncio
    async def test_complete_markdown_document(self):
        """Test preprocessing complete Markdown document."""
        content = """
# Machine Learning Guide

Machine learning is a subset of artificial intelligence.
It enables systems to learn from data.

## Key Concepts

| Concept | Description |
|---------|-------------|
| Supervised Learning | Learning from labeled data |
| Unsupervised Learning | Finding patterns in unlabeled data |

Machine learning algorithms can be categorized into different types.
"""

        result = await preprocess_document(content)

        # Verify metadata
        assert result.metadata.title == "Machine Learning Guide"
        assert result.metadata.word_count > 0
        assert "machine" in result.metadata.keywords
        assert "learning" in result.metadata.keywords
        assert result.metadata.summary is not None

        # Verify tables
        assert len(result.tables) == 1
        assert result.tables[0].headers == ["Concept", "Description"]
        assert len(result.tables[0].rows) == 2

        # Verify processing time
        assert result.processing_time is not None
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_complete_html_document(self):
        """Test preprocessing complete HTML document."""
        content = """
<html>
<head><title>Data Science</title></head>
<body>
<h1>Data Science Overview</h1>
<p>Data science combines statistics and programming.</p>

<table>
    <tr><th>Tool</th><th>Purpose</th></tr>
    <tr><td>Python</td><td>Programming</td></tr>
    <tr><td>R</td><td>Statistics</td></tr>
</table>
</body>
</html>
"""

        result = await preprocess_document(content)

        # Verify metadata
        assert result.metadata.title == "Data Science"
        assert result.metadata.word_count > 0

        # Verify tables
        assert len(result.tables) == 1
        assert result.tables[0].headers == ["Tool", "Purpose"]
        assert len(result.tables[0].rows) == 2

    @pytest.mark.asyncio
    async def test_batch_preprocessing(self):
        """Test batch preprocessing of multiple documents."""
        documents = [
            "# Doc 1\nContent 1",
            "# Doc 2\n| A | B |\n|---|---|\n| 1 | 2 |",
            "# Doc 3\nContent 3",
        ]

        results = []
        for doc in documents:
            result = await preprocess_document(doc)
            results.append(result)

        assert len(results) == 3
        assert results[0].metadata.title == "Doc 1"
        assert len(results[1].tables) == 1
        assert results[2].metadata.title == "Doc 3"
