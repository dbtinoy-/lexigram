"""DatabaseQuerySkill — read-only SELECT queries via DatabaseProviderProtocol."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from lexigram.ai.skills.base import AbstractSkill
from lexigram.ai.skills.exceptions import SkillExecutionError
from lexigram.contracts.ai.skills import SkillDefinition, SkillError, SkillResult
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

_SELECT_RE = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
_LIMIT_RE = re.compile(r"\bLIMIT\s+\d+", re.IGNORECASE)
_DEFAULT_LIMIT = 100


class DatabaseQuerySkill(AbstractSkill):
    """Execute read-only SELECT statements and return row dicts.

    Only ``SELECT`` statements are accepted.  A ``LIMIT`` clause is
    automatically appended when the query does not already contain one,
    capped at *max_rows* (default 100) to prevent runaway reads.

    Args:
        db: A :class:`DatabaseProviderProtocol` instance.
        max_rows: Maximum rows returned per query.
    """

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        max_rows: int = _DEFAULT_LIMIT,
    ) -> None:
        """Initialise the skill with a database provider.

        Args:
            db: DatabaseProviderProtocol for query execution.
            max_rows: Hard cap on returned rows.
        """
        self._db = db
        self._max_rows = max_rows

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition.

        Returns:
            SkillDefinition for the database_query skill.
        """
        return SkillDefinition(
            name="database_query",
            description=(
                "Execute a read-only SELECT SQL query and return the results as "
                "a list of row dicts."
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
        """Execute the SELECT query and return up to *max_rows* rows.

        Args:
            **kwargs: Requires ``query`` (str); accepts ``params`` (dict).

        Returns:
            Ok result with ``rows`` and ``row_count``, or Err if the query
            is not a SELECT or execution fails.
        """
        query: str = kwargs.get("query", "")
        params: dict[str, Any] = kwargs.get("params") or {}

        if not _SELECT_RE.match(query):
            return Err(
                SkillExecutionError(
                    "Only SELECT statements are permitted in database_query."
                )
            )

        if not _LIMIT_RE.search(query):
            query = f"{query.rstrip(';')} LIMIT {self._max_rows}"

        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                rows = await conn.fetch(query, **params)
                row_dicts: list[dict[str, Any]] = [dict(r) for r in rows]
        except (
            Exception
        ) as exc:  # DB driver can raise various infrastructure exceptions
            raise RuntimeError(f"database_query execution failed: {exc}") from exc

        return Ok(
            SkillResult(
                skill_name="database_query",
                success=True,
                output={"rows": row_dicts, "row_count": len(row_dicts)},
            )
        )
