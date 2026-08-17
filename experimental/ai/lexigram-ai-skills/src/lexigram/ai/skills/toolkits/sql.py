"""SQLToolkit - database operations skills."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from lexigram.ai.skills.base import AbstractSkill
from lexigram.ai.skills.exceptions import SkillExecutionError
from lexigram.ai.skills.toolkits.toolkit import Toolkit
from lexigram.contracts.ai.skills import (
    SkillDefinition,
    SkillError,
    SkillProtocol,
    SkillResult,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

_SELECT_RE = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
_LIMIT_RE = re.compile(r"\bLIMIT\s+\d+", re.IGNORECASE)
_DEFAULT_LIMIT = 100


class SQLExecuteSkill(AbstractSkill):
    """Execute SQL queries against a database.

    Only SELECT statements are allowed for safety. A LIMIT clause is
    automatically appended when not present.
    """

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        max_rows: int = _DEFAULT_LIMIT,
    ) -> None:
        """Initialise with database provider.

        Args:
            db: DatabaseProviderProtocol for query execution.
            max_rows: Maximum rows returned per query.
        """
        self._db = db
        self._max_rows = max_rows

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition."""
        return SkillDefinition(
            name="sql_execute",
            description=(
                "Execute a read-only SELECT SQL query and return results as "
                "a list of row dictionaries."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT statement to execute.",
                    },
                    "params": {
                        "type": "object",
                        "description": "Optional named query parameters.",
                        "default": {},
                    },
                },
                "required": ["query"],
            },
            category="database",
            permissions=["db.query"],
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Execute the SELECT query."""
        query: str = kwargs.get("query", "")
        params: dict[str, Any] = kwargs.get("params") or {}

        if not _SELECT_RE.match(query):
            return Err(SkillExecutionError("Only SELECT statements are permitted."))

        if not _LIMIT_RE.search(query):
            query = f"{query.rstrip(';')} LIMIT {self._max_rows}"

        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                rows = await conn.fetch(query, **params)
                row_dicts: list[dict[str, Any]] = [dict(r) for r in rows]
        except Exception as exc:
            raise RuntimeError(f"sql_execute failed: {exc}") from exc

        return Ok(
            SkillResult(
                skill_name="sql_execute",
                success=True,
                output={"rows": row_dicts, "row_count": len(row_dicts)},
            )
        )


class SQLDescribeSkill(AbstractSkill):
    """Describe a table's structure."""

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialise with database provider.

        Args:
            db: DatabaseProviderProtocol for query execution.
        """
        self._db = db

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition."""
        return SkillDefinition(
            name="sql_describe",
            description="Get the column structure of a table.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Name of the table to describe.",
                    },
                },
                "required": ["table"],
            },
            category="database",
            permissions=["db.query"],
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Describe the table structure."""
        table: str = kwargs.get("table", "")

        if not table:
            return Err(SkillExecutionError("Table name is required."))

        query = f"DESCRIBE {table}"

        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                rows = await conn.fetch(query)
                columns = [dict(r) for r in rows]
        except Exception as exc:
            raise RuntimeError(f"sql_describe failed: {exc}") from exc

        return Ok(
            SkillResult(
                skill_name="sql_describe",
                success=True,
                output={"table": table, "columns": columns},
            )
        )


class SQLListTablesSkill(AbstractSkill):
    """List all tables in the database."""

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialise with database provider.

        Args:
            db: DatabaseProviderProtocol for query execution.
        """
        self._db = db

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition."""
        return SkillDefinition(
            name="sql_list_tables",
            description="List all tables in the connected database.",
            parameters_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
            category="database",
            permissions=["db.query"],
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """List all tables."""
        query = "SHOW TABLES"

        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                rows = await conn.fetch(query)
                tables = [dict(r) for r in rows]
        except Exception as exc:
            raise RuntimeError(f"sql_list_tables failed: {exc}") from exc

        return Ok(
            SkillResult(
                skill_name="sql_list_tables",
                success=True,
                output={"tables": tables},
            )
        )


class SQLToolkit(Toolkit):
    """Toolkit providing SQL database operations skills.

    Provides skills for executing SELECT queries, describing tables,
    and listing available tables.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialise with database provider.

        Args:
            db: DatabaseProviderProtocol for query execution.
        """
        super().__init__(
            name="sql",
            description="SQL database operations toolkit",
        )
        self._db = db

    def _get_tools(self) -> tuple[SkillProtocol, ...]:
        """Return the SQL toolkit skills."""
        return (
            SQLExecuteSkill(self._db),
            SQLDescribeSkill(self._db),
            SQLListTablesSkill(self._db),
        )


__all__ = ["SQLDescribeSkill", "SQLExecuteSkill", "SQLListTablesSkill", "SQLToolkit"]
