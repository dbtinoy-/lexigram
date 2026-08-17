"""Unit tests for P1 RAG loaders.

Covers:
- DocxLoader
- ExcelLoader
- EmailLoader
- CodeLoader
- SQLLoader
- WebScraperLoader
"""

from __future__ import annotations

import re
import sys
from types import SimpleNamespace, TracebackType
from typing import Any, Self
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.rag.loaders import p1_loaders
from lexigram.ai.rag.loaders.p1_loaders import (
    CodeLoader,
    DocxLoader,
    EmailLoader,
    ExcelLoader,
    SQLLoader,
    WebScraperLoader,
)
from lexigram.ai.rag.types import RAGError

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class _AsyncContext:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        return False


class _FakeLink:
    def __init__(self, href: str) -> None:
        self._href = href

    def __getitem__(self, key: str) -> str:
        if key != "href":
            raise KeyError(key)
        return self._href


class _FakeSoup:
    """Very small BeautifulSoup stand-in used by WebScraperLoader tests."""

    def __init__(self, html: str, parser: str) -> None:  # noqa: ARG002
        self._html = html

    def __call__(self, tags: list[str]) -> list[Any]:  # noqa: ARG002
        # Simulate soup(["script", ...]) API used for tag removal.
        return []

    def get_text(self, separator: str = "\n", strip: bool = True) -> str:
        text = re.sub(r"<[^>]+>", separator, self._html)
        if strip:
            text = text.strip()
        return text

    def find_all(self, tag: str, href: bool = False) -> list[_FakeLink]:  # noqa: ARG002
        links = re.findall(r'href=["\']([^"\']+)["\']', self._html)
        return [_FakeLink(url) for url in links]


class _FakeResponse:
    def __init__(self, html: str) -> None:
        self._html = html
        self.status = 200
        self.headers: dict[str, str] = {}

    async def text(self) -> str:
        return self._html

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        return False


class _FakeHTTPClient:
    def __init__(self, *, timeout: Any = None) -> None:  # noqa: ARG002
        self._pages = _FAKE_WEB_PAGES

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        return False

    def get(self, url: str, **kwargs: object) -> _FakeResponse:  # noqa: ARG002
        if url not in self._pages:
            raise RuntimeError(f"URL not found: {url}")
        return _FakeResponse(self._pages[url])


_FAKE_WEB_PAGES: dict[str, str] = {}


# ---------------------------------------------------------------------------
# DocxLoader
# ---------------------------------------------------------------------------


class TestDocxLoader:
    @pytest.mark.asyncio
    async def test_load_docx_paragraphs(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "sample.docx"
        path.write_bytes(b"fake-docx")

        class _FakeParagraph:
            def __init__(self, text: str, style: str | None = "Normal") -> None:
                self.text = text
                self.style = SimpleNamespace(name=style) if style else None

        class _FakeDoc:
            paragraphs = [
                _FakeParagraph("First paragraph"),
                _FakeParagraph("   "),
                _FakeParagraph("Second paragraph", style="Heading 1"),
            ]

        fake_docx = SimpleNamespace(Document=lambda _stream: _FakeDoc())
        monkeypatch.setitem(sys.modules, "docx", fake_docx)

        loader = DocxLoader()
        chunks = await loader.load(path)

        assert len(chunks) == 2
        assert chunks[0].metadata["type"] == "docx"
        assert chunks[0].metadata["paragraph_index"] == 0
        assert chunks[1].metadata["style"] == "Heading 1"


# ---------------------------------------------------------------------------
# ExcelLoader
# ---------------------------------------------------------------------------


class TestExcelLoader:
    @pytest.mark.asyncio
    async def test_load_excel_row_mode(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "sample.xlsx"
        path.write_bytes(b"fake-excel")

        class _FakeSheet:
            def __init__(self, title: str, rows: list[tuple[Any, ...]]) -> None:
                self.title = title
                self._rows = rows

            def iter_rows(self, values_only: bool = True):  # noqa: ARG002
                return iter(self._rows)

        class _FakeWorkbook:
            worksheets = [
                _FakeSheet(
                    "Sheet1",
                    [
                        ("name", "score"),
                        ("alice", 10),
                        ("bob", 9),
                    ],
                )
            ]

        fake_openpyxl = SimpleNamespace(
            load_workbook=lambda _stream, data_only=True: _FakeWorkbook()  # noqa: ARG005
        )
        monkeypatch.setitem(sys.modules, "openpyxl", fake_openpyxl)

        loader = ExcelLoader(chunk_per_sheet=False)
        chunks = await loader.load(path)

        assert len(chunks) == 2
        assert "name: alice" in chunks[0].text
        assert chunks[0].metadata["type"] == "excel"
        assert chunks[0].metadata["sheet"] == "Sheet1"

    @pytest.mark.asyncio
    async def test_load_excel_sheet_mode(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "sheet.xlsx"
        path.write_bytes(b"fake-excel")

        class _FakeSheet:
            def __init__(self, title: str, rows: list[tuple[Any, ...]]) -> None:
                self.title = title
                self._rows = rows

            def iter_rows(self, values_only: bool = True):  # noqa: ARG002
                return iter(self._rows)

        class _FakeWorkbook:
            worksheets = [
                _FakeSheet("Main", [("a", "b"), (1, 2)]),
                _FakeSheet("Other", [("x", "y"), (3, 4)]),
            ]

        fake_openpyxl = SimpleNamespace(
            load_workbook=lambda _stream, data_only=True: _FakeWorkbook()  # noqa: ARG005
        )
        monkeypatch.setitem(sys.modules, "openpyxl", fake_openpyxl)

        loader = ExcelLoader(chunk_per_sheet=True)
        chunks = await loader.load(path)

        assert len(chunks) == 2
        assert chunks[0].metadata["sheet"] == "Main"
        assert chunks[1].metadata["sheet"] == "Other"


# ---------------------------------------------------------------------------
# EmailLoader
# ---------------------------------------------------------------------------


class TestEmailLoader:
    @pytest.mark.asyncio
    async def test_load_eml_extracts_headers_and_body(self, tmp_path: Any) -> None:
        path = tmp_path / "mail.eml"
        path.write_text(
            "From: alice@example.com\n"
            "To: bob@example.com\n"
            "Subject: Status Update\n"
            "Date: Sat, 01 Jan 2026 00:00:00 +0000\n"
            'Content-Type: text/plain; charset="utf-8"\n'
            "Content-Transfer-Encoding: 8bit\n"
            "\n"
            "Hello Bob,\nAll systems operational.\n",
            encoding="utf-8",
        )

        loader = EmailLoader()
        chunks = await loader.load(path)

        assert len(chunks) == 1
        chunk = chunks[0]
        assert "Subject: Status Update" in chunk.text
        assert "All systems operational." in chunk.text
        assert chunk.metadata["type"] == "email"
        assert chunk.metadata["from"] == "alice@example.com"


# ---------------------------------------------------------------------------
# CodeLoader
# ---------------------------------------------------------------------------


class TestCodeLoader:
    @pytest.mark.asyncio
    async def test_load_python_code_split_by_definitions(self, tmp_path: Any) -> None:
        path = tmp_path / "sample.py"
        path.write_text(
            "def alpha():\n    return 1\n\nclass Beta:\n    pass\n",
            encoding="utf-8",
        )

        loader = CodeLoader(max_chunk_lines=50)
        chunks = await loader.load(path)

        assert len(chunks) >= 2
        assert chunks[0].metadata["type"] == "code"
        assert chunks[0].metadata["language"] == "py"

    @pytest.mark.asyncio
    async def test_load_unknown_extension_uses_fixed_size_batches(
        self, tmp_path: Any
    ) -> None:
        path = tmp_path / "data.unknown"
        path.write_text(
            "line1\nline2\nline3\nline4\nline5\n",
            encoding="utf-8",
        )

        loader = CodeLoader(max_chunk_lines=2)
        chunks = await loader.load(path)

        assert len(chunks) == 3
        assert chunks[0].metadata["start_line"] == 1
        assert chunks[1].metadata["start_line"] == 3
        assert chunks[2].metadata["start_line"] == 5


# ---------------------------------------------------------------------------
# SQLLoader
# ---------------------------------------------------------------------------


class TestSQLLoader:
    @pytest.mark.asyncio
    async def test_load_sql_rows_batched(self) -> None:
        conn = MagicMock()
        conn.fetch = AsyncMock(
            return_value=[
                {"id": 1, "text": "A"},
                {"id": 2, "text": "B"},
                {"id": 3, "text": "C"},
            ]
        )

        db = MagicMock()
        db.scoped_context = MagicMock(return_value=_AsyncContext())
        db.get_scoped_connection = AsyncMock(return_value=conn)

        loader = SQLLoader(
            db,
            query="SELECT id, text FROM docs",
            text_column="text",
            batch_size=2,
            table_name="docs",
        )

        chunks = await loader.load()

        assert len(chunks) == 2
        assert chunks[0].source == "sql://docs"
        assert chunks[0].metadata["type"] == "sql"
        assert "A" in chunks[0].text
        assert "B" in chunks[0].text

    @pytest.mark.asyncio
    async def test_load_sql_raises_rag_error_on_query_failure(self) -> None:
        conn = MagicMock()
        conn.fetch = AsyncMock(side_effect=RuntimeError("db failure"))

        db = MagicMock()
        db.scoped_context = MagicMock(return_value=_AsyncContext())
        db.get_scoped_connection = AsyncMock(return_value=conn)

        loader = SQLLoader(
            db,
            query="SELECT * FROM docs",
            table_name="docs",
        )

        with pytest.raises(RAGError, match="SQL query failed"):
            await loader.load()


# ---------------------------------------------------------------------------
# WebScraperLoader
# ---------------------------------------------------------------------------


class TestWebScraperLoader:
    @pytest.fixture(autouse=True)
    def _patch_web_dependencies(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(
            sys.modules, "bs4", SimpleNamespace(BeautifulSoup=_FakeSoup)
        )
        monkeypatch.setitem(
            sys.modules,
            "aiohttp",
            SimpleNamespace(
                ClientSession=_FakeHTTPClient,
                ClientTimeout=lambda **kw: None,
            ),
        )

    @pytest.fixture(autouse=True)
    def _fake_public_dns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Resolve every hostname to a single public IP — no live DNS."""
        import ipaddress

        from lexigram.contracts.security import url_safety as contracts_url_safety

        monkeypatch.setattr(
            contracts_url_safety,
            "resolve_hostname",
            lambda _: [ipaddress.ip_address("93.184.216.34")],
        )

    @pytest.mark.asyncio
    async def test_load_web_single_page(self) -> None:
        _FAKE_WEB_PAGES.clear()
        _FAKE_WEB_PAGES["https://example.com"] = (
            "<html><body><h1>Title</h1><p>Hello world</p></body></html>"
        )

        loader = WebScraperLoader(follow_links=False)
        chunks = await loader.load("https://example.com")

        assert len(chunks) == 1
        assert chunks[0].metadata["type"] == "web"
        assert chunks[0].source == "https://example.com"
        assert "Hello world" in chunks[0].text

    @pytest.mark.asyncio
    async def test_load_web_follow_links_with_limit(self) -> None:
        _FAKE_WEB_PAGES.clear()
        _FAKE_WEB_PAGES["https://root.example"] = (
            '<html><body>Root <a href="https://l1.example">L1</a>'
            '<a href="https://l2.example">L2</a></body></html>'
        )
        _FAKE_WEB_PAGES["https://l1.example"] = "<html><body>Link One</body></html>"
        _FAKE_WEB_PAGES["https://l2.example"] = "<html><body>Link Two</body></html>"

        loader = WebScraperLoader(follow_links=True, max_links=1)
        chunks = await loader.load("https://root.example")

        # root + 1 followed link due max_links=1
        assert len(chunks) == 2
        assert chunks[1].metadata["parent"] == "https://root.example"

    @pytest.mark.asyncio
    async def test_load_web_ignores_failed_link_fetches(self) -> None:
        _FAKE_WEB_PAGES.clear()
        _FAKE_WEB_PAGES["https://root.example"] = (
            '<html><body>Root <a href="https://good.example">good</a>'
            '<a href="https://missing.example">missing</a></body></html>'
        )
        _FAKE_WEB_PAGES["https://good.example"] = "<html><body>Good Link</body></html>"

        loader = WebScraperLoader(follow_links=True, max_links=5)
        chunks = await loader.load("https://root.example")

        # root + one successful child; missing link is ignored by design
        assert len(chunks) == 2
        assert chunks[0].source == "https://root.example"

    @pytest.mark.asyncio
    async def test_load_rejects_private_seed(self) -> None:
        loader = WebScraperLoader(follow_links=False)
        with pytest.raises(RAGError, match="publicly reachable"):
            await loader.load("http://169.254.169.254/latest/meta-data/")

    @pytest.mark.asyncio
    async def test_load_skips_unsafe_followed_link(self) -> None:
        _FAKE_WEB_PAGES.clear()
        _FAKE_WEB_PAGES["https://root.example"] = (
            '<html><body>Root <a href="http://10.0.0.5/x">internal</a>'
            '<a href="https://good.example/p">good</a></body></html>'
        )
        _FAKE_WEB_PAGES["https://good.example/p"] = "<html><body>Public</body></html>"
        _FAKE_WEB_PAGES["http://10.0.0.5/x"] = "<html><body>Secret</body></html>"

        loader = WebScraperLoader(follow_links=True, max_links=5)
        chunks = await loader.load("https://root.example")

        assert len(chunks) == 2  # root + only the safe followed link
        assert chunks[1].source == "https://good.example/p"
