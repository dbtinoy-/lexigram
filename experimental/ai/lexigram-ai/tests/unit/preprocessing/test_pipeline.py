"""Tests for PreprocessingPipeline and preprocess_document convenience function."""

import pytest

try:
    from lexigram.ai.rag.preprocessing import (
        MetadataEnricher,
        PreprocessingPipeline,
        TableExtractor,
        preprocess_document,
    )
except ImportError as e:
    pytest.skip(
        f"Skipping tests in module because importing preprocessing failed: {e}",
        allow_module_level=True,
    )


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

        assert len(result.tables) == 1
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

        assert len(result.tables) == 1
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

        assert result.metadata.title == "Machine Learning Guide"
        assert result.metadata.word_count > 0
        assert "machine" in result.metadata.keywords
        assert "learning" in result.metadata.keywords
        assert result.metadata.summary is not None

        assert len(result.tables) == 1
        assert result.tables[0].headers == ["Concept", "Description"]
        assert len(result.tables[0].rows) == 2

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

        assert result.metadata.title == "Data Science"
        assert result.metadata.word_count > 0

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
