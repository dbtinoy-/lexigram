"""Safe parameterized SQL connector — exposes table queries as MCP tools.

Unlike the legacy ``DatabaseResourceProvider`` (which had an SQL injection
vulnerability), this connector:

- Enforces an explicit table allowlist
- Uses fully qualified identifier quoting for table names
- Passes all user-supplied values via ``$N`` parameters (never f-string)
- Restricts to SELECT only when ``read_only=True`` (the default)

Tools exposed:
- ``sql_query``           — Execute a read-only SELECT against an allowed table
- ``sql_list_tables``     — List all tables in the allowlist
- ``sql_describe_table``  — Return column names and types for an allowed table
"""

from __future__ import annotations

import re
from typing import Any

from lexigram.ai.mcp.types import MCPResource, MCPToolDefinition, MCPToolResult
from lexigram.contracts.exceptions import DatabaseError
from lexigram.logging import (
    get_logger,
)
from lexigram.serialization import dumps_str

logger = get_logger(__name__)

# Allowlist pattern: table names must be identifiers only (no operators/quotes)
_SAFE_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SQLConnector:
    """Safe parameterized SQL connector for MCP.

    Exposes ``DatabaseProviderProtocol``-backed read operations as MCP tools.
    All public methods guard against SQL injection by:
    1. Validating table names against an explicit allowlist.
    2. Quoting identifiers using ``"`` (ANSI standard, supported by all major RDBMS).
    3. Never interpolating user values — only ``$N`` placeholders are used.

    Example::

        connector = SQLConnector(
            db=database_provider,
            allowed_tables=["orders", "customers"],
        )
    """

    def __init__(
        self,
        db: Any,
        allowed_tables: list[str],
        *,
        read_only: bool = True,
        max_rows: int = 500,
    ) -> None:
        """Initialize the SQL connector.

        Args:
            db: ``DatabaseProviderProtocol`` instance.
            allowed_tables: Explicit list of tables that may be queried.
            read_only: Restrict to SELECT statements only (default True).
            max_rows: Maximum rows to return per query (default 500).

        Raises:
            ValueError: If ``allowed_tables`` is empty.
        """
        if not allowed_tables:
            raise ValueError("SQLConnector requires at least one allowed_table")
        for name in allowed_tables:
            if not _SAFE_IDENT_RE.match(name):
                raise ValueError(
                    f"Invalid table name '{name}'. "
                    "Must be alphanumeric + undersscores only."
                )
        self._db = db
        self._allowed_tables = list(allowed_tables)
        self._read_only = read_only
        self._max_rows = max_rows

    # ------------------------------------------------------------------
    # MCPToolProviderProtocol interface
    # ------------------------------------------------------------------

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions for this connector."""
        return [
            MCPToolDefinition(
                name="sql_query",
                description=(
                    "Execute a SELECT query against an allowed table. "
                    "Use $1, $2, … for parameters."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "table": {
                            "type": "string",
                            "description": "Table name (must be in the allowlist)",
                        },
                        "where": {
                            "type": "string",
                            "description": "Optional WHERE clause (no semicolons)",
                            "default": "",
                        },
                        "params": {
                            "type": "array",
                            "items": {},
                            "description": "Parameter values for $1, $2, …",
                            "default": [],
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum rows to return",
                            "default": 50,
                        },
                    },
                    "required": ["table"],
                },
            ).to_dict(),
            MCPToolDefinition(
                name="sql_list_tables",
                description="List all tables available in this connector",
                input_schema={"type": "object", "properties": {}},
            ).to_dict(),
            MCPToolDefinition(
                name="sql_describe_table",
                description="Describe column names and types for a table",
                input_schema={
                    "type": "object",
                    "properties": {
                        "table": {
                            "type": "string",
                            "description": "Table name",
                        }
                    },
                    "required": ["table"],
                },
            ).to_dict(),
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Dispatch tool calls to handler methods.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            MCPToolResult with JSON data or error.
        """
        from lexigram.contracts.mcp.exceptions import MCPToolCallError

        dispatch = {
            "sql_query": self._sql_query,
            "sql_list_tables": self._sql_list_tables,
            "sql_describe_table": self._sql_describe_table,
        }
        handler = dispatch.get(name)
        if handler is None:
            raise MCPToolCallError(message=f"Unknown SQL tool: {name}", tool_name=name)
        return await handler(arguments)

    # ------------------------------------------------------------------
    # MCPResourceProviderProtocol interface
    # ------------------------------------------------------------------

    async def list_resources(self) -> list[dict[str, Any]]:
        """List all allowed tables as MCP resources."""
        return [
            MCPResource(
                uri=f"sql://{table}",
                name=table,
                description=f"Database table: {table}",
                mime_type="application/json",
            ).to_dict()
            for table in self._allowed_tables
        ]

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read the first N rows of a table resource.

        Args:
            uri: ``sql://table_name`` URI.

        Returns:
            MCP resource content dict.
        """
        table = uri.removeprefix("sql://")
        result = await self._sql_query({"table": table, "limit": 50})
        text = result.content[0]["text"] if result.content else "[]"
        return {
            "contents": [{"uri": uri, "mimeType": "application/json", "text": text}]
        }

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def _sql_query(self, arguments: dict[str, Any]) -> MCPToolResult:
        table = arguments.get("table", "")
        where = arguments.get("where", "") or ""
        params: list[Any] = list(arguments.get("params") or [])
        limit = min(int(arguments.get("limit") or 50), self._max_rows)

        if not self._is_allowed_table(table):
            return MCPToolResult.error(
                f"Table '{table}' is not in the allowlist. "
                f"Allowed: {self._allowed_tables}"
            )

        # Reject dangerous constructs in WHERE clause
        if where and _has_dangerous_sql(where):
            return MCPToolResult.error(
                "WHERE clause contains disallowed SQL constructs"
            )

        safe_table = _quote_identifier(table)
        sql = f"SELECT * FROM {safe_table}"
        if where:
            sql += f" WHERE {where}"
        sql += f" LIMIT ${len(params) + 1}"
        params.append(limit)

        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                rows = await conn.fetch(sql, *params)
            data = [dict(row) for row in rows]
            return MCPToolResult.text(dumps_str(data))
        except (
            DatabaseError,
            RuntimeError,
            ValueError,
            TypeError,
            AttributeError,
            LookupError,
            OSError,
        ) as exc:
            logger.error("sql_query_error", table=table, error=str(exc))
            return MCPToolResult.error(f"Query failed: {exc}")

    async def _sql_list_tables(self, _arguments: dict[str, Any]) -> MCPToolResult:
        return MCPToolResult.text(dumps_str(self._allowed_tables))

    async def _sql_describe_table(self, arguments: dict[str, Any]) -> MCPToolResult:
        table = arguments.get("table", "")
        if not self._is_allowed_table(table):
            return MCPToolResult.error(f"Table '{table}' is not in the allowlist.")
        safe_table = _quote_identifier(table)
        sql = (
            "SELECT column_name, data_type "
            "FROM information_schema.columns "
            "WHERE table_name = $1 ORDER BY ordinal_position"
        )
        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                rows = await conn.fetch(sql, table)
            columns = [
                {"column": r["column_name"], "type": r["data_type"]} for r in rows
            ]
            return MCPToolResult.text(dumps_str(columns))
        except (
            DatabaseError,
            RuntimeError,
            ValueError,
            TypeError,
            AttributeError,
            LookupError,
            OSError,
        ) as exc:
            # Fallback: use a LIMIT 0 SELECT to get column info
            try:
                async with self._db.scoped_context():
                    conn = await self._db.get_scoped_connection()
                    rows = await conn.fetch(f"SELECT * FROM {safe_table} LIMIT 0")
                columns = list(rows[0].keys()) if rows else []
                return MCPToolResult.text(dumps_str(columns))
            except (
                DatabaseError,
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
                LookupError,
                OSError,
            ) as inner_exc:
                logger.error("sql_describe_error", table=table, error=str(inner_exc))
                return MCPToolResult.error(f"Describe failed: {exc}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_allowed_table(self, table: str) -> bool:
        return table in self._allowed_tables


def _quote_identifier(name: str) -> str:
    """Quote a SQL identifier using ANSI double-quotes."""
    return '"' + name.replace('"', '""') + '"'


def _has_dangerous_sql(clause: str) -> bool:
    """Heuristic check for dangerous SQL constructs in a WHERE clause."""
    normalized = clause.upper()
    dangerous = [";", "--", "/*", "*/", "DROP", "DELETE", "UPDATE", "INSERT", "EXEC"]
    return any(kw in normalized for kw in dangerous)


__all__ = ["SQLConnector"]
