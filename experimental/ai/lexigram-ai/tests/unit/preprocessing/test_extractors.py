"""Tests for TableExtractor and MetadataEnricher."""

import pytest

try:
    from lexigram.ai.rag.preprocessing import MetadataEnricher, OCRPreprocessor, TableExtractor
except ImportError as e:
    pytest.skip(
        f"Skipping tests in module because importing preprocessing failed: {e}",
        allow_module_level=True,
    )


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
        )

        enricher = MetadataEnricher()
        result = await enricher.preprocess(content)

        assert result.metadata.summary is not None
        assert len(result.metadata.summary) > 0
        assert len(result.metadata.summary) <= 200
