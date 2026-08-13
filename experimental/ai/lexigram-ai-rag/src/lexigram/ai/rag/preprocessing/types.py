"""
Document preprocessing types.

Contains dataclasses and enums for document preprocessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DocumentType(str, Enum):
    """Types of documents that can be preprocessed."""

    PDF = "pdf"
    IMAGE = "image"
    HTML = "html"
    MARKDOWN = "markdown"
    TEXT = "text"
    DOCX = "docx"
    UNKNOWN = "unknown"


class TableFormat(str, Enum):
    """Formats for extracted tables."""

    MARKDOWN = "markdown"
    HTML = "html"
    CSV = "csv"
    JSON = "json"


@dataclass
class ExtractedImage:
    """Represents an extracted image from a document.

    Attributes:
        image_id: Unique identifier for the image.
        page_number: Page number where image was found.
        position: Position on page (x, y, width, height).
        alt_text: Alternative text description.
        ocr_text: Text extracted from image via OCR.
        metadata: Additional metadata.
    """

    image_id: str
    page_number: int
    position: tuple[int, int, int, int] | None = None
    alt_text: str | None = None
    ocr_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedTable:
    """Represents an extracted table from a document.

    Attributes:
        table_id: Unique identifier for the table.
        page_number: Page number where table was found.
        headers: Column headers.
        rows: Table rows (list of lists).
        caption: Table caption or title.
        format: Format of the table.
        metadata: Additional metadata.
    """

    table_id: str
    page_number: int
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    caption: str | None = None
    format: TableFormat = TableFormat.MARKDOWN
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert table to Markdown format."""
        if not self.headers and not self.rows:
            return ""

        lines = []

        # Add caption
        if self.caption:
            lines.append(f"**{self.caption}**\n")

        # Add headers
        if self.headers:
            lines.append("| " + " | ".join(self.headers) + " |")
            lines.append("|" + "|".join(["---"] * len(self.headers)) + "|")

        # Add rows
        for row in self.rows:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines) + "\n"

    def to_html(self) -> str:
        """Convert table to HTML format."""
        if not self.headers and not self.rows:
            return ""

        html_parts = []

        # Add caption
        if self.caption:
            html_parts.append(f"<caption>{self.caption}</caption>")

        # Build table
        html_parts.append("<table>")

        # Add headers
        if self.headers:
            html_parts.append("<thead><tr>")
            for header in self.headers:
                html_parts.append(f"<th>{header}</th>")
            html_parts.append("</tr></thead>")

        # Add rows
        html_parts.append("<tbody>")
        for row in self.rows:
            html_parts.append("<tr>")
            for cell in row:
                html_parts.append(f"<td>{cell}</td>")
            html_parts.append("</tr>")
        html_parts.append("</tbody>")

        html_parts.append("</table>")
        return "".join(html_parts)

    def to_csv(self) -> str:
        """Convert table to CSV format."""
        if not self.headers and not self.rows:
            return ""

        lines = []

        # Add headers
        if self.headers:
            lines.append(",".join(self.headers))

        # Add rows
        for row in self.rows:
            lines.append(",".join(row))

        return "\n".join(lines)

    def to_json(self) -> list[dict[str, Any]]:
        """Convert table to JSON-compatible list of dicts."""
        if not self.headers and not self.rows:
            return []

        result: list[dict[str, Any]] = []
        if self.headers:
            for row in self.rows:
                result.append(dict(zip(self.headers, row, strict=False)))
        else:
            for i, row in enumerate(self.rows):
                result.append({"row": i, "data": row})

        return result


@dataclass
class DocumentMetadata:
    """Metadata for a preprocessed document.

    Attributes:
        doc_type: Type of document.
        page_count: Number of pages.
        title: Document title.
        author: Document author.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        language: Document language.
        word_count: Number of words.
        char_count: Number of characters.
        images: List of extracted images.
        tables: List of extracted tables.
        custom_metadata: Additional custom metadata.
    """

    doc_type: DocumentType = DocumentType.UNKNOWN
    page_count: int = 0
    title: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    language: str | None = None
    word_count: int = 0
    char_count: int = 0
    keywords: list[str] = field(default_factory=list)
    summary: str | None = None
    images: list[ExtractedImage] = field(default_factory=list)
    tables: list[ExtractedTable] = field(default_factory=list)
    custom_metadata: dict[str, Any] = field(default_factory=dict)

    def add_image(self, image: ExtractedImage) -> None:
        """Add an extracted image."""
        self.images.append(image)

    def add_table(self, table: ExtractedTable) -> None:
        """Add an extracted table."""
        self.tables.append(table)

    @property
    def custom(self) -> dict[str, Any]:
        """Backwards compatible alias for custom_metadata."""
        return self.custom_metadata

    @property
    def document_type(self) -> DocumentType:
        """Backwards compatible alias for doc_type."""
        return self.doc_type

    def merge(self, other: DocumentMetadata) -> None:
        """Merge another metadata object into this one."""
        if other.title and not self.title:
            self.title = other.title
        if other.author and not self.author:
            self.author = other.author
        if other.language and not self.language:
            self.language = other.language
        if other.word_count > 0 and self.word_count == 0:
            self.word_count = other.word_count
        if other.char_count > 0 and self.char_count == 0:
            self.char_count = other.char_count
        if (
            other.doc_type != DocumentType.UNKNOWN
            and self.doc_type == DocumentType.UNKNOWN
        ):
            self.doc_type = other.doc_type

        self.keywords.extend(k for k in other.keywords if k not in self.keywords)
        self.images.extend(other.images)
        self.tables.extend(other.tables)
        self.custom_metadata.update(other.custom_metadata)
        if other.summary and not self.summary:
            self.summary = other.summary
