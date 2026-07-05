"""Unit tests for UniversalDocumentParser."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lexigram.ai.workers.document_ingestion.parser import UniversalDocumentParser
from lexigram.ai.workers.document_ingestion.types import Document
from lexigram.contracts.ai.exceptions import RAGError


class TestUniversalDocumentParser:
    """Tests for UniversalDocumentParser class."""

    @pytest.fixture
    def parser(self) -> UniversalDocumentParser:
        """Create parser instance for testing."""
        return UniversalDocumentParser()

    @pytest.fixture
    def temp_txt_file(self, tmp_path: Path) -> Path:
        """Create a temporary text file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("This is a plain text document.")
        return file_path

    @pytest.fixture
    def temp_md_file(self, tmp_path: Path) -> Path:
        """Create a temporary markdown file."""
        file_path = tmp_path / "test.md"
        file_path.write_text("# Header\n\nSome **markdown** content.")
        return file_path

    @pytest.fixture
    def temp_html_file(self, tmp_path: Path) -> Path:
        """Create a temporary HTML file."""
        file_path = tmp_path / "test.html"
        file_path.write_text("<html><body><p>Hello <strong>World</strong></p></body></html>")
        return file_path

    @pytest.fixture
    def temp_pdf_file(self, tmp_path: Path) -> Path:
        """Create a temporary PDF file."""
        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"mock pdf content")
        return file_path

    @pytest.mark.asyncio
    async def test_parse_txt_file(self, parser: UniversalDocumentParser, temp_txt_file: Path) -> None:
        """Test parsing a plain text file."""
        doc = await parser.parse(temp_txt_file)

        assert isinstance(doc, Document)
        assert "This is a plain text document." in doc.content
        assert doc.metadata["file_type"] == ".txt"
        assert doc.metadata["file_name"] == "test.txt"

    @pytest.mark.asyncio
    async def test_parse_md_file(self, parser: UniversalDocumentParser, temp_md_file: Path) -> None:
        """Test parsing a markdown file."""
        doc = await parser.parse(temp_md_file)

        assert isinstance(doc, Document)
        assert "Header" in doc.content
        assert doc.metadata["file_type"] == ".md"
        assert "header" in doc.metadata

    @pytest.mark.asyncio
    async def test_parse_html_file(self, parser: UniversalDocumentParser, temp_html_file: Path) -> None:
        """Test extracting text from HTML file."""
        doc = await parser.parse(temp_html_file)

        assert isinstance(doc, Document)
        assert "Hello" in doc.content
        assert "World" in doc.content
        assert doc.metadata["file_type"] == ".html"
        assert doc.metadata["type"] == "html"

    @pytest.mark.asyncio
    async def test_parse_pdf_file(self, parser: UniversalDocumentParser, temp_pdf_file: Path) -> None:
        """Test extracting text from PDF file."""
        with patch("importlib.import_module") as mock_import:
            mock_pypdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "PDF page 1 text"
            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_pypdf.PdfReader.return_value = mock_reader
            mock_import.return_value = mock_pypdf

            doc = await parser.parse(temp_pdf_file)

        assert isinstance(doc, Document)
        assert "PDF page 1 text" in doc.content
        assert doc.metadata["file_type"] == ".pdf"
        assert doc.metadata["type"] == "pdf"

    @pytest.mark.asyncio
    async def test_parse_unsupported_returns_error(self, parser: UniversalDocumentParser, tmp_path: Path) -> None:
        """Test unsupported file extension raises ValueError."""
        unsupported_file = tmp_path / "test.xyz"
        unsupported_file.write_text("content")

        with pytest.raises(ValueError, match="Unsupported file type"):
            await parser.parse(unsupported_file)

    @pytest.mark.asyncio
    async def test_parser_handles_empty_file(self, parser: UniversalDocumentParser, tmp_path: Path) -> None:
        """Test empty file returns empty content."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        doc = await parser.parse(empty_file)

        assert doc.content == ""
        assert doc.metadata["file_type"] == ".txt"

    @pytest.mark.asyncio
    async def test_parser_raises_on_missing_file(self, parser: UniversalDocumentParser, tmp_path: Path) -> None:
        """Test FileNotFoundError is raised for non-existent file."""
        missing_file = tmp_path / "missing.txt"

        with pytest.raises(FileNotFoundError, match="Document not found"):
            await parser.parse(missing_file)

    def test_supported_extensions(self, parser: UniversalDocumentParser) -> None:
        """Test supported_extensions property returns list of extensions."""
        extensions = parser.supported_extensions

        assert ".txt" in extensions
        assert ".md" in extensions
        assert ".html" in extensions
        assert ".pdf" in extensions
        assert ".htm" in extensions
        assert ".markdown" in extensions

    @pytest.mark.asyncio
    async def test_extract_metadata(self, parser: UniversalDocumentParser, temp_txt_file: Path) -> None:
        """Test extract_metadata returns file metadata."""
        metadata = await parser.extract_metadata(temp_txt_file)

        assert "file_path" in metadata
        assert "file_name" in metadata
        assert "file_size" in metadata
        assert "file_type" in metadata

    @pytest.mark.asyncio
    async def test_parse_with_special_characters(self, parser: UniversalDocumentParser, tmp_path: Path) -> None:
        """Test parser handles files with special UTF-8 characters."""
        file_path = tmp_path / "unicode.txt"
        file_path.write_text("Hello 世界 🎉 émoji")

        doc = await parser.parse(file_path)

        assert "Hello" in doc.content
        assert "世界" in doc.content

    @pytest.fixture
    def doc_root(self, tmp_path: Path) -> Path:
        """Create the allowed document root with one real file inside."""
        root = tmp_path / "doc_root"
        root.mkdir()
        (root / "safe.txt").write_text("inside the root", encoding="utf-8")
        return root

    @pytest.mark.asyncio
    async def test_parse_with_allowed_root_accepts_file_inside(
        self, doc_root: Path
    ) -> None:
        """Test a file inside allowed_root parses unchanged."""
        parser = UniversalDocumentParser(allowed_root=doc_root)

        doc = await parser.parse(doc_root / "safe.txt")

        assert doc.metadata["file_name"] == "safe.txt"

    @pytest.mark.asyncio
    async def test_parse_with_allowed_root_rejects_dotdot_escape(
        self, doc_root: Path, tmp_path: Path
    ) -> None:
        """Test a dotdot-relative source outside allowed_root raises RAGError."""
        secret = tmp_path / "secret.txt"
        secret.write_text("secret", encoding="utf-8")
        parser = UniversalDocumentParser(allowed_root=doc_root)

        with pytest.raises(RAGError, match="outside the allowed root"):
            await parser.parse(doc_root / ".." / "secret.txt")

    @pytest.mark.asyncio
    async def test_parse_with_allowed_root_rejects_absolute_escape(
        self, doc_root: Path, tmp_path: Path
    ) -> None:
        """Test an absolute source outside allowed_root raises RAGError."""
        secret = tmp_path / "secret.txt"
        secret.write_text("secret", encoding="utf-8")
        parser = UniversalDocumentParser(allowed_root=doc_root)

        with pytest.raises(RAGError, match="outside the allowed root"):
            await parser.parse(secret)

    @pytest.mark.asyncio
    async def test_parse_with_allowed_root_rejects_symlink_escape(
        self, doc_root: Path, tmp_path: Path
    ) -> None:
        """Test a symlink pointing outside allowed_root raises RAGError."""
        secret = tmp_path / "secret.txt"
        secret.write_text("secret", encoding="utf-8")
        link = doc_root / "link.txt"
        link.symlink_to(secret)
        parser = UniversalDocumentParser(allowed_root=doc_root)

        with pytest.raises(RAGError, match="outside the allowed root"):
            await parser.parse(link)

    @pytest.mark.asyncio
    async def test_extract_metadata_with_allowed_root_rejects_escape(
        self, doc_root: Path, tmp_path: Path
    ) -> None:
        """Test extract_metadata enforces the same containment check."""
        secret = tmp_path / "secret.txt"
        secret.write_text("secret", encoding="utf-8")
        parser = UniversalDocumentParser(allowed_root=doc_root)

        with pytest.raises(RAGError, match="outside the allowed root"):
            await parser.extract_metadata(doc_root / ".." / "secret.txt")
