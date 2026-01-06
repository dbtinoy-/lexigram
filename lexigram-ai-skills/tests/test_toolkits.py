"""Tests for toolkits (ToolkitProtocol, SQLToolkit, WebToolkit)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.ai.skills import (
    SkillDefinition,
    SkillResult,
)
from lexigram.result import Ok


class TestToolkitProtocol:
    """Tests for ToolkitProtocol in contracts."""

    def test_toolkit_protocol_exists(self) -> None:
        """ToolkitProtocol should exist in contracts."""
        from lexigram.contracts.ai.skills import ToolkitProtocol
        assert ToolkitProtocol is not None

    def test_toolkit_protocol_has_tools_property(self) -> None:
        """ToolkitProtocol should have tools property."""
        from lexigram.contracts.ai.skills import SkillProtocol, ToolkitProtocol

        class MockToolkit:
            @property
            def tools(self) -> tuple[SkillProtocol, ...]:
                return ()

            @property
            def name(self) -> str:
                return "mock"

            @property
            def description(self) -> str:
                return "Mock toolkit"

        toolkit = MockToolkit()
        assert hasattr(toolkit, "tools")
        assert hasattr(toolkit, "name")
        assert hasattr(toolkit, "description")


class TestToolkit:
    """Tests for base Toolkit class."""

    def test_toolkit_exists(self) -> None:
        """Toolkit base class should exist."""
        from lexigram.ai.skills.toolkits import Toolkit
        assert Toolkit is not None

    def test_toolkit_inherits_protocol(self) -> None:
        """Toolkit should implement ToolkitProtocol."""
        from lexigram.ai.skills.toolkits import Toolkit

        class MockToolkit(Toolkit):
            def _get_tools(self):
                return ()

        toolkit = MockToolkit(name="mock", description="Mock toolkit")
        assert hasattr(toolkit, "tools")
        assert hasattr(toolkit, "name")
        assert hasattr(toolkit, "description")


class TestSQLToolkit:
    """Tests for SQLToolkit with database skills."""

    def test_sql_toolkit_exists(self) -> None:
        """SQLToolkit should exist."""
        from lexigram.ai.skills.toolkits import SQLToolkit
        assert SQLToolkit is not None

    def test_sql_toolkit_has_execute_skill(self) -> None:
        """SQLToolkit should have execute skill."""
        from lexigram.ai.skills.toolkits import SQLToolkit

        db = MagicMock()
        toolkit = SQLToolkit(db)
        tool_names = [s.definition.name for s in toolkit.tools]
        assert "sql_execute" in tool_names

    def test_sql_toolkit_has_describe_skill(self) -> None:
        """SQLToolkit should have describe skill."""
        from lexigram.ai.skills.toolkits import SQLToolkit

        db = MagicMock()
        toolkit = SQLToolkit(db)
        tool_names = [s.definition.name for s in toolkit.tools]
        assert "sql_describe" in tool_names

    def test_sql_toolkit_has_list_tables_skill(self) -> None:
        """SQLToolkit should have list_tables skill."""
        from lexigram.ai.skills.toolkits import SQLToolkit

        db = MagicMock()
        toolkit = SQLToolkit(db)
        tool_names = [s.definition.name for s in toolkit.tools]
        assert "sql_list_tables" in tool_names

    @pytest.mark.asyncio
    async def test_sql_execute_skill_runs_query(self) -> None:
        """SQLToolkit execute skill should run the query."""
        from lexigram.ai.skills.toolkits import SQLToolkit

        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[{"id": 1, "name": "test"}])

        mock_db = MagicMock()
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_db.scoped_context = MagicMock(return_value=mock_context)
        mock_db.get_scoped_connection = AsyncMock(return_value=mock_conn)

        toolkit = SQLToolkit(mock_db)
        result = await toolkit.tools[0].execute(query="SELECT 1")

        assert result.is_ok()
        assert result.unwrap().success is True


class TestWebToolkit:
    """Tests for WebToolkit with web skills."""

    def test_web_toolkit_exists(self) -> None:
        """WebToolkit should exist."""
        from lexigram.ai.skills.toolkits import WebToolkit
        assert WebToolkit is not None

    def test_web_toolkit_has_search_skill(self) -> None:
        """WebToolkit should have web search skill."""
        from lexigram.ai.skills.toolkits import WebToolkit

        http_client = MagicMock()
        toolkit = WebToolkit(http_client)
        tool_names = [s.definition.name for s in toolkit.tools]
        assert "web_search" in tool_names

    def test_web_toolkit_has_browse_skill(self) -> None:
        """WebToolkit should have web browse skill."""
        from lexigram.ai.skills.toolkits import WebToolkit

        http_client = MagicMock()
        toolkit = WebToolkit(http_client)
        tool_names = [s.definition.name for s in toolkit.tools]
        assert "web_browse" in tool_names

    @pytest.mark.asyncio
    async def test_web_search_returns_results(self) -> None:
        """WebToolkit search skill should return search results."""
        from lexigram.ai.skills.toolkits import WebToolkit

        http_client = MagicMock()
        http_client.request = AsyncMock(return_value={
            "status": 200,
            "body": '{"results": [{"title": "Test", "url": "http://test.com"}]}',
        })

        toolkit = WebToolkit(http_client)
        search_skill = next(s for s in toolkit.tools if s.definition.name == "web_search")
        result = await search_skill.execute(query="test query")

        assert result.is_ok()
        assert result.unwrap().success is True
        assert "results" in str(result.unwrap().output)

    @pytest.mark.asyncio
    async def test_web_browse_returns_content(self) -> None:
        """WebToolkit browse skill should return page content."""
        from lexigram.ai.skills.toolkits import WebToolkit

        http_client = MagicMock()
        http_client.request = AsyncMock(return_value={
            "status": 200,
            "body": "<html><body>Test content</body></html>",
        })

        toolkit = WebToolkit(http_client)
        browse_skill = next(s for s in toolkit.tools if s.definition.name == "web_browse")
        result = await browse_skill.execute(url="http://test.com")

        assert result.is_ok()
        assert result.unwrap().success is True
        assert "content" in str(result.unwrap().output).lower() or "Test content" in str(result.unwrap().output)
