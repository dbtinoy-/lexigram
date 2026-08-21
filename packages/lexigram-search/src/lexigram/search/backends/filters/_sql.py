"""SQL family filter rendering (postgres/mysql/sqlite)."""

from __future__ import annotations

from typing import Any

from lexigram.search.backends.filters._validation import (
    FilterRenderError,
    _validate_filters,
)

_SQL_OPS: dict[str, str] = {
    "eq": "=",
    "ne": "<>",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "in": "IN",
    "nin": "NOT IN",
}


def _sql_condition(
    expr: Callable[[str], str],
    key: str,
    op: str,
    value: Any,
    params: list[Any],
    placeholder: Callable[[int], str],
    offset: int,
) -> str:
    """Render a single leaf predicate to a SQL condition.

    Placeholder ordinals start at *offset* (1-based) so the fragment can
    follow earlier parameters in the same statement.
    """
    if op == "contains":
        ph = placeholder(len(params) + offset)
        params.append(f"%{value}%")
        return f"{expr(key)} LIKE {ph}"
    if op == "exists":
        return f"{expr(key)} IS {'NOT NULL' if value else 'NULL'}"
    if op in ("in", "nin"):
        start = len(params) + offset
        slots = ", ".join(placeholder(start + i) for i in range(len(value)))
        params.extend(value)
        return f"{expr(key)} {_SQL_OPS[op]} ({slots})"
    ph = placeholder(len(params) + offset)
    params.append(value)
    return f"{expr(key)} {_SQL_OPS[op]} {ph}"


def _sql_expr(
    expr: Callable[[str], str],
    sub: dict[str, Any],
    params: list[Any],
    placeholder: Callable[[int], str],
    offset: int,
) -> str:
    """Render one sub-filter dict to an atomic SQL condition (AND semantics).

    Group children are parenthesized. Lone ``$or``/``$and`` groups and
    single-condition frames are returned bare, so a top-level group does
    not gain stray outer parentheses.
    """
    many = len(sub) > 1
    conditions: list[str] = []
    for key, value in sub.items():
        if key == "$not":
            if not isinstance(value, dict):
                raise FilterRenderError("$not must contain a single filter dict")
            conditions.append(
                f"NOT ({_sql_expr(expr, value, params, placeholder, offset)})"
            )
            continue
        if key in ("$and", "$or"):
            if not isinstance(value, list):
                raise FilterRenderError(f"{key} must be a list of filter dicts")
            rendered = [
                f"({_sql_expr(expr, group, params, placeholder, offset)})"
                for group in value
            ]
            joined = " OR ".join(rendered) if key == "$or" else " AND ".join(rendered)
            conditions.append(f"({joined})" if many else joined)
            continue
        if isinstance(value, dict):
            if "contains" in value:
                conditions.append(
                    _sql_condition(
                        expr,
                        key,
                        "contains",
                        value["contains"],
                        params,
                        placeholder,
                        offset,
                    )
                )
                continue
            if "exists" in value:
                conditions.append(
                    _sql_condition(
                        expr,
                        key,
                        "exists",
                        value["exists"],
                        params,
                        placeholder,
                        offset,
                    )
                )
                continue
            if "in" in value or "nin" in value:
                op = "in" if "in" in value else "nin"
                conditions.append(
                    _sql_condition(
                        expr, key, op, value[op], params, placeholder, offset
                    )
                )
                continue
            if "ne" in value:
                conditions.append(
                    _sql_condition(
                        expr, key, "ne", value["ne"], params, placeholder, offset
                    )
                )
                continue
            for op, val in value.items():
                conditions.append(
                    _sql_condition(expr, key, op, val, params, placeholder, offset)
                )
            continue
        if isinstance(value, (list, tuple)):
            conditions.append(
                _sql_condition(
                    expr, key, "in", list(value), params, placeholder, offset
                )
            )
        else:
            conditions.append(
                _sql_condition(expr, key, "eq", value, params, placeholder, offset)
            )
    joined = " AND ".join(conditions)
    return joined


def _render_sql(
    filters: dict[str, Any],
    expr: Callable[[str], str],
    placeholder: Callable[[int], str],
    offset: int = 1,
) -> tuple[str, list[Any]]:
    """Render a filter dict to a parameterized SQL WHERE fragment.

    Args:
        filters: Canonical filter dict.
        expr: Field -> SQL expression builder (json column access).
        placeholder: 1-based ordinal -> placeholder text builder.
        offset: 1-based ordinal of the first placeholder in this statement.
    """
    _validate_filters(filters)
    params: list[Any] = []
    clause = _sql_expr(expr, filters, params, placeholder, offset)
    return clause, params


def render_postgres(filters: dict[str, Any], offset: int = 1) -> tuple[str, list[Any]]:
    """Render a filter dict to a Postgres WHERE fragment on the ``document`` column.

    Values reference the jsonb ``document`` column via the ``->>`` text
    extraction (dotted field paths resolve as JSON paths).

    Args:
        filters: Canonical filter dict.
        offset: 1-based ordinal of the first placeholder in the target
            statement (defaults to 1).

    Returns:
        A ``(clause, params)`` pair; placeholders are ``$1..$n``.

    Raises:
        FilterRenderError: If the filter dict violates the dialect.
    """
    return _render_sql(
        filters,
        expr=lambda field: f"document->>'{field}'",
        placeholder=lambda n: f"${n}",
        offset=offset,
    )


def render_mysql(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    """Render a filter dict to a MySQL WHERE fragment on the ``document`` column.

    Values reference the JSON ``document`` column via
    ``JSON_UNQUOTE(JSON_EXTRACT(document, '$.field'))``.

    Args:
        filters: Canonical filter dict.

    Returns:
        A ``(clause, params)`` pair; placeholders are ``%s``.

    Raises:
        FilterRenderError: If the filter dict violates the dialect.
    """
    return _render_sql(
        filters,
        expr=lambda field: f"JSON_UNQUOTE(JSON_EXTRACT(document, '$.{field}'))",
        placeholder=lambda _: "%s",
    )


def render_sqlite(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    """Render a filter dict to a SQLite WHERE fragment on the ``document`` column.

    Values reference the JSON ``document`` column via
    ``json_extract(document, '$.field')``.

    Args:
        filters: Canonical filter dict.

    Returns:
        A ``(clause, params)`` pair; placeholders are ``?``.

    Raises:
        FilterRenderError: If the filter dict violates the dialect.
    """
    return _render_sql(
        filters,
        expr=lambda field: f"json_extract(document, '$.{field}')",
        placeholder=lambda _: "?",
    )


