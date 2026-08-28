"""Advanced filter management for DataTable with presets, URL sharing, and validation."""

from __future__ import annotations

from datetime import UTC
import inspect
from typing import Any
from urllib.parse import parse_qs, urlencode

from lexigram.admin.services.filter_types import FilterDefinition, FilterPreset
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str, loads_str

logger = get_logger(__name__)


class FilterManager:
    """Manage DataTable filters with presets, URL encoding, validation, and search translation."""

    def __init__(
        self,
        filter_definitions: list[FilterDefinition] | None = None,
        translator: Any | None = None,
    ) -> None:
        """Initialize filter manager.

        Args:
            filter_definitions: List of available filter definitions.
            translator: ``FilterSetTranslator`` used to convert the active
                filter dict into a :class:`~lexigram.search.engine.SearchQuery`.
                Defaults to a bare :class:`FilterSetTranslator` instance when
                ``None`` and ``lexigram-search`` is installed (it is stateless,
                so the default is safe). Pass ``None`` when search is not needed.
        """
        self.filter_definitions = {f.field: f for f in (filter_definitions or [])}
        self._presets: dict[str, FilterPreset] = {}
        if translator is not None:
            self._translator: Any = translator
        else:
            self._translator = None

    async def process_request(
        self,
        query_params: Any,
        state_filters: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], set[str]]:
        """
        Process request query parameters into a validated filter dictionary (async).
        """
        filters: dict[str, Any] = {}
        consumed: set[str] = set()

        for field, definition in self.filter_definitions.items():
            # Support both explicit Filter types and raw definitions
            f_inst = definition.filter
            raw_val = None

            if f_inst and hasattr(f_inst, "get_value_from_request"):
                try:
                    # Check if it's an async method
                    if inspect.iscoroutinefunction(f_inst.get_value_from_request):
                        raw_val = await f_inst.get_value_from_request(query_params)
                    else:
                        raw_val = f_inst.get_value_from_request(query_params)
                except (
                    ConnectionError,
                    RuntimeError,
                    ValueError,
                    TypeError,
                    AttributeError,
                ):
                    raw_val = None

            # Fallback to direct query param access if not handled by filter instance
            if raw_val is None:
                raw_val = query_params.get(field)

            if raw_val is not None and raw_val != "":
                # Handle default exclusion
                default = None
                if hasattr(f_inst, "get_default"):
                    default = f_inst.get_default()  # type: ignore[union-attr]
                elif definition.default_value is not None:
                    default = definition.default_value

                if raw_val != default:
                    # Parse typed value
                    try:
                        if hasattr(f_inst, "from_url_param"):
                            parsed = f_inst.from_url_param(raw_val)  # type: ignore[union-attr]
                        else:
                            # Try JSON or raw
                            try:
                                parsed = loads_str(raw_val)
                            except (ValueError, TypeError):
                                parsed = raw_val
                        filters[field] = parsed
                    except (ValueError, TypeError):
                        filters[field] = raw_val

            # Track consumed params
            if hasattr(f_inst, "get_consumed_params"):
                consumed.update(f_inst.get_consumed_params())  # type: ignore[union-attr]
            else:
                consumed.add(field)

        # Merge anonymous filters from state if provided
        if state_filters:
            filters |= {k: v for k, v in state_filters.items() if k not in consumed}

        return filters, consumed

    async def validate_filters(
        self,
        filters: dict[str, Any],
    ) -> tuple[bool, dict[str, str]]:
        """
        Validate filter values against definitions (async).
        """
        errors: dict[str, str] = {}

        for field, value in filters.items():
            if field not in self.filter_definitions:
                errors[field] = f"Unknown filter field: {field}"
                continue

            definition = self.filter_definitions[field]

            # Check required
            if definition.required and (value is None or value == ""):
                errors[field] = f"{definition.label or field} is required"
                continue

            # Skip validation if empty and not required
            if value is None or value == "":
                continue

            # Options validation via concrete Filter instances
            if definition.filter is not None and hasattr(
                definition.filter,
                "get_options",
            ):
                try:
                    if inspect.iscoroutinefunction(definition.filter.get_options):
                        opts = await definition.filter.get_options()
                    else:
                        opts = definition.filter.get_options()
                except Exception:  # noqa: BLE001 — user-supplied callable; must catch broadly
                    logger.exception(
                        "Failed to get options for filter %s; skipping options validation",
                        field,
                    )
                    opts = []

                # Support list or dict option storage (only validate if opts available)
                if opts:
                    if isinstance(value, list):
                        invalid = list(filter(lambda v: v not in opts, value))
                        if invalid:
                            errors[field] = (
                                f"Invalid value for {definition.label or field}"
                            )
                            continue
                    elif value not in opts:
                        errors[field] = f"Invalid value for {definition.label or field}"
                        continue

            # Custom validator (catch exceptions from validator)
            if definition.validator:
                try:
                    if inspect.iscoroutinefunction(definition.validator):
                        valid = await definition.validator(value)
                    else:
                        valid = definition.validator(value)
                except Exception:  # noqa: BLE001 — user-supplied callable; must catch broadly
                    logger.exception("Validator raised exception for filter %s", field)
                    valid = False

                if not valid:
                    errors[field] = f"Invalid value for {definition.label or field}"
                    continue

        return len(errors) == 0, errors

    def encode_to_url(self, filters: dict[str, Any]) -> str:
        """
        Encode filters to URL query string.
        """
        # Remove empty values
        clean_filters = {k: v for k, v in filters.items() if v is not None and v != ""}

        # Convert to query string
        params = {}
        for key, value in clean_filters.items():
            if isinstance(value, (list, dict)):
                params[f"filter[{key}]"] = dumps_str(value)
            else:
                params[f"filter[{key}]"] = str(value)

        return urlencode(params)

    def decode_from_url(self, query_string: str) -> dict[str, Any]:
        """
        Decode filters from URL query string.
        """
        params = parse_qs(query_string.lstrip("?"))
        filters: dict[str, Any] = {}

        for key, values in params.items():
            if key.startswith("filter[") and key.endswith("]"):
                field = key[7:-1]  # Extract field name
                value = values[0] if values else None

                # Try to parse JSON for complex values
                if value:
                    try:
                        filters[field] = loads_str(value)
                    except (ValueError, TypeError):
                        filters[field] = value

        return filters

    def get_default_filters(self) -> dict[str, Any]:
        """
        Get default filter values from definitions.
        """
        defaults = {}
        for field, definition in self.filter_definitions.items():
            if definition.default_value is not None:
                defaults[field] = definition.default_value
        return defaults

    async def create_preset(
        self,
        name: str,
        filters: dict[str, Any],
        user_id: int | None = None,
        is_default: bool = False,
        is_shared: bool = False,
    ) -> FilterPreset:
        """
        Create a filter preset (async).
        """
        from datetime import datetime

        preset = FilterPreset(
            name=name,
            filters=filters.copy(),
            user_id=user_id,
            is_default=is_default,
            is_shared=is_shared,
            created_at=datetime.now(UTC).isoformat(),
        )

        # Generate preset key
        key = f"{user_id}:{name}" if user_id else name
        self._presets[key] = preset

        return preset

    async def get_preset(
        self,
        name: str,
        user_id: int | None = None,
    ) -> FilterPreset | None:
        """
        Get a saved preset (async).
        """
        key = f"{user_id}:{name}" if user_id else name
        return self._presets.get(key)

    async def list_presets(
        self,
        user_id: int | None = None,
        include_shared: bool = True,
    ) -> list[FilterPreset]:
        """
        List available presets (async).
        """
        presets = []

        for preset in self._presets.values():
            # User-specific presets
            if (
                (user_id and preset.user_id == user_id)
                or (include_shared and preset.is_shared)
                or preset.user_id is None
            ):
                presets.append(preset)

        return presets

    async def delete_preset(self, name: str, user_id: int | None = None) -> bool:
        """
        Delete a preset (async).
        """
        key = f"{user_id}:{name}" if user_id else name
        if key in self._presets:
            del self._presets[key]
            return True
        return False

    def get_active_filter_badges(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Get active filter information for display as badges.
        """
        badges = []

        for field, value in filters.items():
            if value is None or value == "":
                continue

            definition = self.filter_definitions.get(field)
            label = definition.label if definition else field

            # Format value for display
            if isinstance(value, list):
                display_value = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                display_value = dumps_str(value)
            else:
                display_value = str(value)

            # Determine badge type from filter class name if possible
            if definition and getattr(definition, "filter", None):
                badge_type = definition.filter.__class__.__name__.lower()
            else:
                badge_type = "text"

            badges.append(
                {
                    "field": field,
                    "label": label,
                    "value": display_value,
                    "type": badge_type,
                },
            )

        return badges

    def clear_all_filters(self) -> dict[str, Any]:
        """
        Clear all filters and return defaults.
        """
        return self.get_default_filters()

    def has_active_filters(self, filters: dict[str, Any]) -> bool:
        """
        Check if any filters are currently active.
        """
        defaults = self.get_default_filters()

        for field, value in filters.items():
            if value is None or value == "":
                continue

            # Check against default
            if field in defaults:
                if value != defaults[field]:
                    return True
            else:
                return True

        return False

    async def apply_preset(
        self,
        name: str,
        user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Apply a saved preset and return filter values (async)."""
        preset = await self.get_preset(name, user_id)
        if preset:
            return preset.filters.copy()
        return None

    # ------------------------------------------------------------------
    # Search integration
    # ------------------------------------------------------------------

    def to_filter_set(
        self,
        filters: dict[str, Any],
        *,
        search_query: str | None = None,
        order_by: str | None = None,
        order_dir: str = "asc",
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        """Convert an active filter dict to a contract-neutral filter-set payload.

        Each entry in *filters* is mapped to a condition payload using
        operator inference:

        * ``list`` value  → ``FilterOperator.IN``
        * ``None`` value  → ``FilterOperator.IS_NULL``
        * all other values → ``FilterOperator.EQ``

        Empty strings and ``None`` values are dropped (same convention as
        :meth:`encode_to_url`).

        Args:
            filters: Active filter dict (field → value) as produced by
                :meth:`process_request`.
            search_query: Optional free-text query forwarded to
                :attr:`~lexigram.search.filterset.FilterSet.search_query`.
            order_by: Field name to sort by.
            order_dir: Sort direction — ``"asc"`` (default) or ``"desc"``.
            page: 1-based page number.
            page_size: Results per page.

        Returns:
            A dictionary payload with conditions and paging/sorting metadata,
            ready for ``to_search_query`` translation.
        """
        conditions: list[dict[str, Any]] = []
        for field, value in filters.items():
            if value is None:
                conditions.append(
                    {"field": field, "operator": "is_null", "value": None}
                )
            elif value == "":
                continue
            elif isinstance(value, list):
                conditions.append({"field": field, "operator": "in", "value": value})
            else:
                conditions.append({"field": field, "operator": "eq", "value": value})
        return {
            "conditions": tuple(conditions),
            "order_by": order_by,
            "order_dir": order_dir,
            "page": page,
            "page_size": page_size,
            "search_query": search_query,
        }

    def to_search_query(
        self,
        filters: dict[str, Any],
        *,
        search_query: str | None = None,
        order_by: str | None = None,
        order_dir: str = "asc",
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        """Translate the active filter dict directly into a search-query payload.

        Convenience wrapper that calls :meth:`to_filter_set` followed by
        ``translator.translate()`` when a translator was provided.

        Args:
            filters: Active filter dict (field → value).
            search_query: Optional free-text query string.
            order_by: Field name to sort by.
            order_dir: Sort direction — ``"asc"`` or ``"desc"``.
            page: 1-based page number.
            page_size: Results per page.

        Returns:
            A search-query payload ready to pass to a search backend.

        Raises:
            RuntimeError: If no translator was configured.
        """
        if self._translator is None:
            raise RuntimeError(
                "FilterManager.to_search_query() requires a translator object "
                "injected via the constructor.",
            )
        filter_set = self.to_filter_set(
            filters,
            search_query=search_query,
            order_by=order_by,
            order_dir=order_dir,
            page=page,
            page_size=page_size,
        )
        return self._translator.translate(filter_set)


__all__ = [
    "FilterDefinition",
    "FilterManager",
    "FilterPreset",
]
