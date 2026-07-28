"""Filter mixin for SQLRepository: ``_apply_filters_to_query``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar

from lexigram.contracts.data.identifiers import Column
from lexigram.logging import get_logger
from lexigram.sql.lib import parse_date_safely
from lexigram.sql.repositories.filter_objects import normalize_filters
from lexigram.sql.repositories.filters import FilterOperatorRegistry

logger = get_logger(__name__)


class _FilterMixin:
    """Provides ``_apply_filters_to_query`` for SQL repositories."""

    _filter_registry: ClassVar[FilterOperatorRegistry] = FilterOperatorRegistry()

    async def _apply_filters_to_query(
        self,
        query: str,
        params: list[Any],
        filters: dict[str, Any],
        include_deleted: bool = False,
        filter_expressions: tuple[Any, ...] = (),
    ) -> str:
        """Helper to apply search and sophisticated filters to a SQL query."""
        search_term = filters.pop("search", None)
        search_fields = filters.pop("search_fields", [])

        where_parts = []

        if self.soft_delete_enabled and not include_deleted:  # type: ignore[attr-defined]
            where_parts.append("deleted_at IS NULL")

        for typed_filter in normalize_filters(filter_expressions):
            where_part, filter_params = typed_filter.to_sql()
            where_parts.append(where_part)
            params.extend(filter_params)

        for field_spec, value in filters.items():

            def _std(v: Any) -> Any:
                if isinstance(v, list):
                    return list(map(_std, v))
                if isinstance(v, str):
                    lower_v = v.lower()
                    if lower_v in ("on", "true"):
                        return True
                    if lower_v in ("off", "false"):
                        return False
                return v

            check_val = value[0] if isinstance(value, list) and value else value
            parsed_check = parse_date_safely(check_val)
            if isinstance(parsed_check, (date, datetime)) or any(
                d in field_spec
                for d in [
                    "date",
                    "time",
                    "created_at",
                    "updated_at",
                    "deleted_at",
                    "last_active",
                ]
            ):
                logger.info(
                    "Skipping date-related filter in query: %s=%s",
                    field_spec,
                    value,
                )
                continue

            if "__" in field_spec:
                raw_field, op = field_spec.split("__", 1)
                field = str(Column(raw_field))
                where_part, params = self._filter_registry.apply_operator(
                    op,
                    field,
                    value,
                    params,
                )
                where_parts.append(where_part)
            else:
                safe_field = str(Column(field_spec))
                where_parts.append(f"{safe_field} = ?")
                params.append(_std(value))

        if search_term and search_fields:
            search_clause = " OR ".join(
                f"{Column(field)} ILIKE ?" for field in search_fields
            )
            where_parts.append(f"({search_clause})")
            params.extend([f"%{search_term}%" for _ in search_fields])
            logger.info(
                "search.apply_ilike",
                search_term=search_term,
                search_fields=list(search_fields),
                clause=search_clause,
            )

        if self.multi_tenant:  # type: ignore[attr-defined]
            tenant_id = self._db_ctx.tenant_id if self._db_ctx is not None else None  # type: ignore[attr-defined]
            if tenant_id:
                where_parts.append("tenant_id = ?")
                params.append(tenant_id)
            else:
                logger.warning(
                    "Query on multi-tenant table %s with no tenant_id in context",
                    self.table_name,  # type: ignore[attr-defined]
                )

        if where_parts:
            has_where = False
            upper_query = query.upper()
            if " WHERE " in upper_query:
                last_paren = upper_query.rfind(")")
                if last_paren == -1:
                    has_where = True
                else:
                    has_where = upper_query.find(" WHERE ", last_paren) != -1

            keyword = " AND " if has_where else " WHERE "
            query += keyword + " AND ".join(where_parts)

        return query
