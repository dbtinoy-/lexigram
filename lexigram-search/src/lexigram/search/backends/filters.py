"""Canonical search filter dialect and per-backend rendering.

All search backends receive one canonical filter dictionary shape via
``search(..., filters=...)``:

* ``{field: value}`` — equality predicate (a bare ``list`` value is
  treated as ``in``).
* ``{field: {"op": value}}`` — operator predicate with ``op`` one of
  ``in`` / ``nin`` / ``ne`` / ``gt`` / ``gte`` / ``lt`` / ``lte`` /
  ``contains`` / ``exists`` (multiple comparison keys such as
  ``{"gte": a, "lte": b}`` express a range).
* ``{"$and": [sub, ...]}``, ``{"$or": [sub, ...]}`` — boolean groups of
  sub-filter dicts.
* ``{"$not": sub}`` — negation of a sub-filter dict.

This module is the single place that renders that dialect into each
backend's native filter syntax.  Backends pick their renderer through
:func:`render_filters` (registry-based dispatch), keeping the canonical
form portable and the per-engine syntax isolated.
"""

from __future__ import annotations

from collections.abc import Callable
import re
from typing import Any

_FIELD_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")

_OPERATOR_KEYS = frozenset(
    {"in", "nin", "ne", "gt", "gte", "lt", "lte", "contains", "exists"}
)
_BOOLEAN_KEYS = frozenset({"$and", "$or", "$not"})
_COMPARISON_SYMBOLS = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}


class FilterRenderError(ValueError):
    """Raised when a filter dict cannot be rendered for a backend."""


def _validate_filters(filters: dict[str, Any]) -> None:
    """Validate a filter dict against the canonical dialect.

    Args:
        filters: The filter dict to validate.

    Raises:
        FilterRenderError: If the structure violates the dialect (bad field
            names, unknown operators, malformed boolean groups).
    """
    for key, value in filters.items():
        if key in _BOOLEAN_KEYS:
            if key == "$not":
                if not isinstance(value, dict):
                    raise FilterRenderError("$not must contain a single filter dict")
                _validate_filters(value)
                continue
            if not isinstance(value, list) or not all(
                isinstance(item, dict) for item in value
            ):
                raise FilterRenderError(f"{key} must be a list of filter dicts")
            for item in value:
                _validate_filters(item)
            continue
        if not _FIELD_NAME_RE.fullmatch(key):
            raise FilterRenderError(
                f"invalid field name {key!r}; only A-Za-z0-9._- are allowed"
            )
        if isinstance(value, dict):
            unknown = set(value) - _OPERATOR_KEYS
            if unknown:
                raise FilterRenderError(
                    f"unsupported operator(s) {sorted(unknown)} on field {key!r}"
                )


# ---------------------------------------------------------------------------
# Elasticsearch / OpenSearch
# ---------------------------------------------------------------------------


def _es_clauses(sub: dict[str, Any]) -> list[dict[str, Any]]:
    """Render one sub-filter dict to an ES clause list (AND semantics)."""
    clauses: list[dict[str, Any]] = []
    for key, value in sub.items():
        if key == "$not":
            if not isinstance(value, dict):
                raise FilterRenderError("$not must contain a single filter dict")
            clauses.append({"bool": {"must_not": _es_clauses(value)}})
            continue
        if key in ("$and", "$or"):
            if not isinstance(value, list):
                raise FilterRenderError(f"{key} must be a list of filter dicts")
            groups = [item for group in value for item in _es_clauses(group)]
            if key == "$or":
                clauses.append({"bool": {"should": groups, "minimum_should_match": 1}})
            else:
                clauses.extend(groups)
            continue
        if isinstance(value, dict):
            if "contains" in value:
                clauses.append(
                    {
                        "wildcard": {
                            key: {
                                "value": f"*{value['contains']}*",
                                "case_insensitive": True,
                            }
                        }
                    }
                )
                continue
            if "exists" in value:
                exists_clause = {"exists": {"field": key}}
                clauses.append(
                    exists_clause
                    if value["exists"]
                    else {"bool": {"must_not": exists_clause}}
                )
                continue
            if "in" in value:
                clauses.append({"terms": {key: list(value["in"])}})
                continue
            if "nin" in value:
                clauses.append(
                    {"bool": {"must_not": [{"terms": {key: list(value["nin"])}}]}}
                )
                continue
            if "ne" in value:
                clauses.append({"bool": {"must_not": [{"term": {key: value["ne"]}}]}})
                continue
            clauses.append({"range": {key: value}})
            continue
        if isinstance(value, (list, tuple)):
            clauses.append({"terms": {key: list(value)}})
        else:
            clauses.append({"term": {key: value}})
    return clauses


def render_elasticsearch(filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Render a filter dict to Elasticsearch ``bool`` filter clauses.

    Args:
        filters: Canonical filter dict.

    Returns:
        A list of ES query clauses; the caller wraps them in
        ``{"bool": {"filter": [...]}}`` (or ``must`` when empty).

    Raises:
        FilterRenderError: If the filter dict violates the dialect.
    """
    _validate_filters(filters)
    return _es_clauses(filters)


def render_opensearch(filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Render a filter dict to OpenSearch ``bool`` filter clauses.

    OpenSearch shares the Elasticsearch query DSL; see
    :func:`render_elasticsearch`.
    """
    return render_elasticsearch(filters)


# ---------------------------------------------------------------------------
# Meilisearch (filter-expression string)
# ---------------------------------------------------------------------------


def _meili_value(value: Any) -> str:
    """Format a scalar as a Meilisearch filter literal."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return f'"{value}"'


def _meili_expr(sub: dict[str, Any]) -> str:
    """Render one sub-filter dict to an atomic Meilisearch expression.

    Group children are parenthesized. Lone ``$or``/``$and`` groups and
    single-condition frames are returned bare, so a top-level group does
    not gain stray outer parentheses.
    """
    many = len(sub) > 1
    parts: list[str] = []
    for key, value in sub.items():
        if key == "$not":
            if not isinstance(value, dict):
                raise FilterRenderError("$not must contain a single filter dict")
            parts.append(f"NOT ({_meili_expr(value)})")
            continue
        if key in ("$and", "$or"):
            if not isinstance(value, list):
                raise FilterRenderError(f"{key} must be a list of filter dicts")
            rendered = [f"({_meili_expr(group)})" for group in value]
            joined = " OR ".join(rendered) if key == "$or" else " AND ".join(rendered)
            parts.append(f"({joined})" if many else joined)
            continue
        if isinstance(value, dict):
            if "contains" in value:
                # Meilisearch filters only support equality/prefix matching;
                # "contains" degrades to a prefix equality filter.
                parts.append(f"{key} = {_meili_value(value['contains'])}")
                continue
            if "exists" in value:
                raise FilterRenderError(
                    "'exists' cannot be expressed in a Meilisearch filter"
                )
            if "in" in value:
                members = ", ".join(_meili_value(v) for v in value["in"])
                parts.append(f"{key} IN [{members}]")
                continue
            if "nin" in value:
                members = ", ".join(_meili_value(v) for v in value["nin"])
                parts.append(f"{key} NOT IN [{members}]")
                continue
            if "ne" in value:
                parts.append(f"{key} != {_meili_value(value['ne'])}")
                continue
            comparisons = [
                f"{key} {_COMPARISON_SYMBOLS[op]} {_meili_value(val)}"
                for op, val in value.items()
            ]
            parts.append(" and ".join(comparisons))
            continue
        if isinstance(value, (list, tuple)):
            members = ", ".join(_meili_value(v) for v in value)
            parts.append(f"{key} IN [{members}]")
        else:
            parts.append(f"{key} = {_meili_value(value)}")
    joined = " AND ".join(parts)
    return joined


def render_meilisearch(filters: dict[str, Any]) -> str:
    """Render a filter dict to a Meilisearch ``filter`` expression string.

    Args:
        filters: Canonical filter dict.

    Returns:
        A Meilisearch filter expression (``"status = \\"active\\""``,
        ``"score >= 80"``, ``"(a) OR (b)"``, ...).

    Raises:
        FilterRenderError: If the filter dict violates the dialect or uses
            an operator Meilisearch cannot express.
    """
    _validate_filters(filters)
    return _meili_expr(filters)


# ---------------------------------------------------------------------------
# Typesense (filter-expression string)
# ---------------------------------------------------------------------------


def _typesense_value(value: Any) -> str:
    """Format a scalar as a Typesense filter literal."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _typesense_expr(sub: dict[str, Any]) -> str:
    """Render one sub-filter dict to an atomic Typesense expression.

    Group children are parenthesized. Lone ``$or``/``$and`` groups and
    single-condition frames are returned bare, so a top-level group does
    not gain stray outer parentheses.
    """
    many = len(sub) > 1
    parts: list[str] = []
    for key, value in sub.items():
        if key == "$not":
            if not isinstance(value, dict):
                raise FilterRenderError("$not must contain a single filter dict")
            parts.append(f"!({_typesense_expr(value)})")
            continue
        if key in ("$and", "$or"):
            if not isinstance(value, list):
                raise FilterRenderError(f"{key} must be a list of filter dicts")
            rendered = [f"({_typesense_expr(group)})" for group in value]
            joined = " || ".join(rendered) if key == "$or" else " && ".join(rendered)
            parts.append(f"({joined})" if many else joined)
            continue
        if isinstance(value, dict):
            if "contains" in value:
                parts.append(f"{key}:contains({_typesense_value(value['contains'])})")
                continue
            if "exists" in value:
                raise FilterRenderError(
                    "'exists' cannot be expressed in a Typesense filter"
                )
            if "in" in value:
                members = ",".join(_typesense_value(v) for v in value["in"])
                parts.append(f"{key}:[{members}]")
                continue
            if "nin" in value:
                members = ",".join(_typesense_value(v) for v in value["nin"])
                parts.append(f"!({key}:[{members}])")
                continue
            if "ne" in value:
                parts.append(f"{key}:!={_typesense_value(value['ne'])}")
                continue
            for op, val in value.items():
                parts.append(f"{key}:{_COMPARISON_SYMBOLS[op]}{_typesense_value(val)}")
            continue
        if isinstance(value, (list, tuple)):
            members = ",".join(_typesense_value(v) for v in value)
            parts.append(f"{key}:[{members}]")
        else:
            parts.append(f"{key}:{_typesense_value(value)}")
    joined = " && ".join(parts)
    return joined


def render_typesense(filters: dict[str, Any]) -> str:
    """Render a filter dict to a Typesense ``filter_by`` expression string.

    Args:
        filters: Canonical filter dict.

    Returns:
        A Typesense filter expression (``"status:active"``,
        ``"score:>=80"``, ``"(a) && (b)"``, ...).

    Raises:
        FilterRenderError: If the filter dict violates the dialect or uses
            an operator Typesense cannot express.
    """
    _validate_filters(filters)
    return _typesense_expr(filters)


# ---------------------------------------------------------------------------
# MongoDB (native query document)
# ---------------------------------------------------------------------------


def _mongo_sub(sub: dict[str, Any]) -> dict[str, Any]:
    """Render one sub-filter dict to a MongoDB query document."""
    doc: dict[str, Any] = {}
    for key, value in sub.items():
        if key == "$not":
            if not isinstance(value, dict):
                raise FilterRenderError("$not must contain a single filter dict")
            doc.update({"$nor": [_mongo_sub(value)]})
            continue
        if key in ("$and", "$or"):
            if not isinstance(value, list):
                raise FilterRenderError(f"{key} must be a list of filter dicts")
            doc.update({key: [_mongo_sub(group) for group in value]})
            continue
        if isinstance(value, dict):
            if "contains" in value:
                doc[key] = {
                    "$regex": re.escape(str(value["contains"])),
                    "$options": "i",
                }
                continue
            if "exists" in value:
                doc[key] = {"$exists": bool(value["exists"])}
                continue
            if "in" in value:
                doc[key] = {"$in": list(value["in"])}
                continue
            if "nin" in value:
                doc[key] = {"$nin": list(value["nin"])}
                continue
            if "ne" in value:
                doc[key] = {"$ne": value["ne"]}
                continue
            doc[key] = {f"${op}": val for op, val in value.items()}
            continue
        if isinstance(value, (list, tuple)):
            doc[key] = {"$in": list(value)}
        elif isinstance(value, str) and "*" in value:
            doc[key] = {"$regex": value.replace("*", ".*"), "$options": "i"}
        else:
            doc[key] = value
    return doc


def render_mongodb(filters: dict[str, Any]) -> dict[str, Any]:
    """Render a filter dict to a MongoDB query document.

    Args:
        filters: Canonical filter dict.

    Returns:
        A MongoDB query document (``{"status": "active"}``,
        ``{"score": {"$gte": 80}}``, ``{"$or": [...]}``, ...).

    Raises:
        FilterRenderError: If the filter dict violates the dialect.
    """
    _validate_filters(filters)
    return _mongo_sub(filters)


# ---------------------------------------------------------------------------
# SQL backends (Postgres / MySQL / SQLite) — WHERE clause with parameters
# ---------------------------------------------------------------------------

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


def render_memory(filters: dict[str, Any]) -> dict[str, Any]:
    """Pass a filter dict through unchanged after validation.

    In-memory backends keep the canonical dialect as their native form.

    Args:
        filters: Canonical filter dict.

    Returns:
        The same filter dict.

    Raises:
        FilterRenderError: If the filter dict violates the dialect.
    """
    _validate_filters(filters)
    return filters


_RENDERERS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "elasticsearch": render_elasticsearch,
    "opensearch": render_opensearch,
    "meilisearch": render_meilisearch,
    "typesense": render_typesense,
    "mongodb": render_mongodb,
    "postgres": render_postgres,
    "mysql": render_mysql,
    "sqlite": render_sqlite,
    "memory": render_memory,
}


def render_filters(dialect: str, filters: dict[str, Any]) -> Any:
    """Render a canonical filter dict for a named backend dialect.

    Args:
        dialect: Backend dialect name (``elasticsearch``, ``opensearch``,
            ``meilisearch``, ``typesense``, ``mongodb``, ``postgres``,
            ``mysql``, ``sqlite``, ``memory``).
        filters: Canonical filter dict to render.

    Returns:
        Backend-native filter representation: ES/OpenSearch clause list,
        Meilisearch/Typesense filter string, MongoDB query document,
        SQL ``(clause, params)`` pair, or the validated dict itself for
        in-memory backends.

    Raises:
        FilterRenderError: If the dialect is unknown or the filter dict
            violates the canonical dialect.
    """
    renderer = _RENDERERS.get(dialect)
    if renderer is None:
        raise FilterRenderError(f"unknown filter dialect {dialect!r}")
    return renderer(filters)


__all__ = [
    "FilterRenderError",
    "render_elasticsearch",
    "render_filters",
    "render_meilisearch",
    "render_memory",
    "render_mongodb",
    "render_mysql",
    "render_opensearch",
    "render_postgres",
    "render_sqlite",
    "render_typesense",
]
