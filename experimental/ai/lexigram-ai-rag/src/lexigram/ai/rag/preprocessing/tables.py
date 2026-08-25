"""
Table extractor for extracting structured tables from documents.

Note: This is a simplified implementation. In production,
integrate with libraries like camelot, tabula, or deep learning models.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING


from lexigram.ai.rag.preprocessing.base import AbstractPreprocessor
from lexigram.ai.rag.preprocessing.document import PreprocessedDocument
from lexigram.ai.rag.preprocessing.types import (
    DocumentMetadata,
    DocumentType,
    ExtractedTable,
    TableFormat,
)


class TableExtractor(AbstractPreprocessor):
    """Table extractor for extracting structured tables from documents.

    Note: This is a simplified implementation. In production,
    integrate with libraries like camelot, tabula, or deep learning models.
    """

    def __init__(self, table_format: TableFormat = TableFormat.MARKDOWN):
        """Initialize table extractor.

        Args:
            table_format: Format for extracted tables.
        """
        super().__init__("table_extractor")
        self.table_format = table_format

    async def preprocess(
        self,
        content: str,
        **kwargs,
    ) -> PreprocessedDocument:
        """Extract tables from document.

        Args:
            content: Document content (HTML, Markdown, or text).
            **kwargs: Additional parameters.

        Returns:
            Preprocessed document with extracted tables.
        """
        tables = self._extract_tables(content)

        # Remove tables from text, replace with references
        processed_text = content
        for i, table in enumerate(tables):
            processed_text = processed_text.replace(
                self._get_table_marker(i),
                f"[Table {i + 1}: {table.caption or 'Untitled'}]",
            )

        metadata = DocumentMetadata(
            doc_type=self._detect_document_type(content),
            word_count=len(processed_text.split()),
        )

        return PreprocessedDocument(
            content=processed_text,
            metadata=metadata,
            tables=tables,
            raw_content=content,
        )

    def _extract_tables(self, content: str) -> list[ExtractedTable]:
        """Extract tables from content.

        Args:
            content: Document content.

        Returns:
            List of extracted tables.
        """
        tables = []

        # Extract Markdown tables
        markdown_tables = self._extract_markdown_tables(content)
        tables.extend(markdown_tables)

        # Extract HTML tables
        html_tables = self._extract_html_tables(content)
        tables.extend(html_tables)

        return tables

    def _extract_markdown_tables(self, content: str) -> list[ExtractedTable]:
        """Extract tables from Markdown content.

        Args:
            content: Markdown content.

        Returns:
            List of extracted tables.
        """
        tables = []

        # Simple Markdown table pattern: | col1 | col2 |
        # Followed by separator: |------|------|
        # Followed by rows: | val1 | val2 |

        # Find table blocks
        lines = content.split("\n")
        i = 0
        table_id = 0

        while i < len(lines):
            line = lines[i].strip()

            # Check if line looks like a table row
            if line.startswith("|") and line.endswith("|"):
                # Potential table start
                table_lines = [line]
                i += 1

                # Collect all consecutive table lines
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith("|") and next_line.endswith("|"):
                        table_lines.append(next_line)
                        i += 1
                    else:
                        break

                # Parse table
                if len(table_lines) >= 2:  # At least header + separator
                    table = self._parse_markdown_table(table_lines, table_id)
                    if table:
                        tables.append(table)
                        table_id += 1
            else:
                i += 1

        return tables

    def _parse_markdown_table(
        self,
        lines: list[str],
        table_id: int,
    ) -> ExtractedTable | None:
        """Parse Markdown table from lines.

        Args:
            lines: Table lines.
            table_id: Table identifier.

        Returns:
            Extracted table or None.
        """
        if len(lines) < 2:
            return None

        # Parse headers
        header_line = lines[0].strip("|").strip()
        headers = list(map(str.strip, header_line.split("|")))

        # Skip separator line (line 1)
        # Parse rows
        rows = []
        for line in lines[2:]:
            row_line = line.strip("|").strip()
            row = list(map(str.strip, row_line.split("|")))
            if len(row) == len(headers):  # Valid row
                rows.append(row)

        return ExtractedTable(
            table_id=f"table_{table_id}",
            page_number=0,  # Unknown for text content
            headers=headers,
            rows=rows,
            format=TableFormat.MARKDOWN,
        )

    def _extract_html_tables(self, content: str) -> list[ExtractedTable]:
        """Extract tables from HTML content.

        Args:
            content: HTML content.

        Returns:
            List of extracted tables.
        """
        tables = []

        # Simple HTML table extraction using regex
        # In production, use proper HTML parser like BeautifulSoup
        table_pattern = r"<table[^>]*>(.*?)</table>"
        table_matches = re.findall(table_pattern, content, re.DOTALL | re.IGNORECASE)

        for i, table_html in enumerate(table_matches):
            table = self._parse_html_table(table_html, i)
            if table:
                tables.append(table)

        return tables

    def _parse_html_table(
        self,
        html: str,
        table_id: int,
    ) -> ExtractedTable | None:
        """Parse HTML table.

        Args:
            html: HTML table content.
            table_id: Table identifier.

        Returns:
            Extracted table or None.
        """
        # Extract headers from <th> tags
        header_pattern = r"<th[^>]*>(.*?)</th>"
        header_matches = re.findall(header_pattern, html, re.DOTALL | re.IGNORECASE)
        headers = list(map(self._clean_html, header_matches))

        # Extract rows from <tr> tags
        row_pattern = r"<tr[^>]*>(.*?)</tr>"
        row_matches = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)

        rows = []
        for row_html in row_matches:
            # Extract cells from <td> tags
            cell_pattern = r"<td[^>]*>(.*?)</td>"
            cell_matches = re.findall(cell_pattern, row_html, re.DOTALL | re.IGNORECASE)
            row = list(map(self._clean_html, cell_matches))
            if row:  # Valid row
                rows.append(row)

        if not headers or not rows:
            return None

        return ExtractedTable(
            table_id=f"table_{table_id}",
            page_number=0,  # Unknown for HTML content
            headers=headers,
            rows=rows,
            format=self.table_format,
        )

    def _clean_html(self, html_text: str) -> str:
        """Clean HTML tags from text.

        Args:
            html_text: Text with HTML tags.

        Returns:
            Clean text.
        """
        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", "", html_text)
        return clean.strip()

    def _detect_document_type(self, content: str) -> DocumentType:
        """Detect document type from content.

        Args:
            content: Document content.

        Returns:
            Detected document type.
        """
        if "<table>" in content.lower():
            return DocumentType.HTML
        if "|" in content and "|" in content.split("\n", maxsplit=1)[0]:
            return DocumentType.MARKDOWN
        return DocumentType.TEXT

    def _get_table_marker(self, table_index: int) -> str:
        """Get marker for table in content.

        Args:
            table_index: Index of table.

        Returns:
            Table marker string.
        """
        return f"[TABLE_MARKER_{table_index}]"
