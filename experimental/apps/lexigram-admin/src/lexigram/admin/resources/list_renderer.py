from __future__ import annotations

"""List view rendering for admin resources.

Composes the column-spec helpers (:mod:`..list_columns`) and the
paginated data fetcher (:mod:`..list_query`) into the DataTable-driven
list view for an admin resource.
"""

from copy import copy
from html import escape
import inspect
from typing import Any
from urllib.parse import parse_qsl, urlencode

from starlette.responses import HTMLResponse

from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.observability.admin_metrics import AdminMetrics
from lexigram.admin.resources.config import TableConfiguration
from lexigram.admin.resources.list_columns import (
    build_columns,
    get_bulk_actions,
    get_filter_options,
    get_header_actions,
    get_row_actions,
)
from lexigram.admin.resources.list_query import ListDataFetcher
from lexigram.admin.resources.urls import admin_prefix_from_request
from lexigram.admin.state.context import wants_fragment
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.ui import TableState, Zones, render_to_string

logger = get_logger(__name__)
_MASKED_FIELD_VALUE = "[REDACTED]"


@inject
class ListRenderer:
    """Handles rendering of list views for admin resources."""

    def __init__(
        self,
        config: AdminConfig,
        resource_name: str,
        renderer: AdminRenderer,
        metrics: AdminMetrics | None = None,
    ):
        self._config = config
        self.resource_name = resource_name
        self._renderer = renderer
        self._metrics = metrics or AdminMetrics(None)
        self._fetcher = ListDataFetcher(resource_name, metrics)

    @staticmethod
    def _request_permission_service(request: Any) -> Any | None:
        """Resolve the mounted field-permission service, when available."""
        try:
            app = request.app
        except (AttributeError, KeyError, RuntimeError):
            app = None
        service = getattr(getattr(app, "state", None), "permission_service", None)
        if service is not None and callable(
            getattr(service, "should_mask_field", None)
        ):
            return service
        try:
            state = request.state
        except (AttributeError, KeyError, RuntimeError):
            state = None
        service = getattr(state, "permission_service", None)
        return (
            service
            if service is not None
            and callable(getattr(service, "should_mask_field", None))
            else None
        )

    @staticmethod
    def _record_value(record: Any, field_name: str) -> Any:
        """Read a top-level field from dict-like or object records."""
        if isinstance(record, dict):
            return record.get(field_name)
        return getattr(record, field_name, None)

    @staticmethod
    def _masked_record(record: Any, fields: set[str]) -> Any:
        """Return an isolated record copy with sensitive values redacted."""
        if isinstance(record, dict):
            masked = dict(record)
            masked.update(dict.fromkeys(fields, _MASKED_FIELD_VALUE))
            return masked

        model_copy = getattr(record, "model_copy", None)
        if callable(model_copy):
            try:
                return model_copy(update=dict.fromkeys(fields, _MASKED_FIELD_VALUE))
            except (AttributeError, TypeError, ValueError):
                pass

        try:
            masked = copy(record)
            for name in fields:
                setattr(masked, name, _MASKED_FIELD_VALUE)
            return masked
        except (AttributeError, TypeError, ValueError):
            # Last resort: a plain mapping is safer than returning the
            # original object, whose sensitive attributes would leak.
            try:
                values = dict(vars(record))
            except (AttributeError, TypeError, ValueError):
                values = {}
            values.update(dict.fromkeys(fields, _MASKED_FIELD_VALUE))
            return values

    async def _mask_items(
        self,
        items: list[Any],
        *,
        source_columns: Any,
        user: Any,
        permission_service: Any | None,
    ) -> list[Any]:
        """Apply field masking before records reach any table renderer."""
        if not items or user is None or permission_service is None:
            return items

        field_names = {
            str(getattr(column, "name", ""))
            for column in source_columns or []
            if getattr(column, "name", None)
        }
        schema = getattr(permission_service, "get_schema", None)
        if callable(schema):
            try:
                permission_schema = schema(self.resource_name)
                field_names.update(
                    str(name) for name in getattr(permission_schema, "fields", {})
                )
            except Exception:  # noqa: BLE001 — renderer must remain available
                logger.exception("admin.list_permission_schema_resolution_failed")

        masked_fields: set[str] = set()
        checker = permission_service.should_mask_field
        for field_name in field_names:
            try:
                result = checker(user, self.resource_name, field_name)
                if inspect.isawaitable(result):
                    result = await result
                if result and any(
                    self._record_value(item, field_name) is not None for item in items
                ):
                    masked_fields.add(field_name)
            except Exception:  # noqa: BLE001 — masking must fail closed
                logger.exception(
                    "admin.list_field_mask_check_failed",
                    resource=self.resource_name,
                    field=field_name,
                )
                if any(
                    self._record_value(item, field_name) is not None for item in items
                ):
                    masked_fields.add(field_name)

        if not masked_fields:
            return items
        return [self._masked_record(item, masked_fields) for item in items]

    def _permissions_for_request(
        self,
        request,
        user: Any | None = None,
    ) -> dict[str, bool] | None:
        """Normalize request-bound RBAC state for the DataTable renderer.

        ``None`` means no permission context was installed (useful for
        standalone component callers). Once auth middleware installs a
        permission attribute, malformed or unavailable values fail closed.
        Direct user permissions are used only when middleware did not install
        a permission attribute at all; a present ``None`` remains a denial.
        """
        state = getattr(request, "state", None)
        if state is None:
            return None

        if hasattr(state, "permissions"):
            raw = getattr(state, "permissions", None)
            if raw is None:
                return {
                    "can_view": False,
                    "can_create": False,
                    "can_update": False,
                    "can_delete": False,
                }
        else:
            request_user = user if user is not None else getattr(state, "user", None)
            raw = getattr(request_user, "permissions", None)
            if raw is None:
                scope = getattr(request, "scope", None)
                scope_user = scope.get("user") if isinstance(scope, dict) else None
                raw = getattr(scope_user, "permissions", None)
            if raw is None:
                return None

        resource = self.resource_name
        has_method = getattr(raw, "has", None)
        if callable(has_method):
            has = has_method
        elif isinstance(raw, dict) and any(
            key in raw for key in ("can_view", "can_create", "can_update", "can_delete")
        ):
            return {
                key: bool(raw.get(key, False))
                for key in ("can_view", "can_create", "can_update", "can_delete")
            }
        elif isinstance(raw, (set, frozenset, list, tuple)):
            values = {str(value) for value in raw}

            def has(permission: str) -> bool:
                return (
                    permission in values or "*" in values or f"{resource}.*" in values
                )
        else:
            return {
                "can_view": False,
                "can_create": False,
                "can_update": False,
                "can_delete": False,
            }

        from lexigram.admin.auth.permission_scheme import candidate_permissions

        def _granted(action: str) -> bool:
            return any(has(perm) for perm in candidate_permissions(resource, action))

        return {
            "can_view": _granted("view"),
            "can_create": _granted("create"),
            "can_update": _granted("update"),
            "can_delete": _granted("delete"),
        }

    @staticmethod
    def _available_fields(source_columns, resource) -> set[str]:
        """Return fields that may safely be addressed by URL-driven state."""
        # Columns arrive in two shapes. Declarative resources get
        # `cls.columns = list(cls.fields)` (base.py), which yields plain
        # field-name strings, while hand-written resources use Column
        # objects. Reading only `.name` returned an empty allowlist for the
        # string form, so _sanitize_table_state rejected every sort field
        # and quietly reset it to None -- sorting looked dead even though
        # the URL updated.
        fields = set()
        for column in source_columns or []:
            if isinstance(column, str):
                if column:
                    fields.add(column)
                continue
            name = getattr(column, "name", None)
            if name:
                fields.add(str(name))
        if fields:
            return fields

        model = getattr(resource, "model", None)
        model_fields = getattr(model, "model_fields", None) or getattr(
            model,
            "__fields__",
            None,
        )
        return {str(name) for name in (model_fields or {})}

    def _sanitize_table_state(
        self, state: TableState, table_config, source_columns, resource
    ):
        """Whitelist URL-controlled sort/group fields before data access/rendering."""
        allowed_fields = self._available_fields(source_columns, resource)
        default_sort = getattr(table_config, "default_sort_by", None)
        safe_default_sort = default_sort if default_sort in allowed_fields else None

        sort_by = state.sort_by
        sort_order = state.sort_order
        if sort_by:
            descending_prefix = sort_by.startswith("-")
            candidate = sort_by[1:] if descending_prefix else sort_by
            if candidate not in allowed_fields:
                sort_by = safe_default_sort
                sort_order = getattr(table_config, "default_sort_order", "asc")
            else:
                sort_by = candidate
                if descending_prefix:
                    sort_order = "desc"
        elif default_sort and default_sort not in allowed_fields:
            sort_by = None

        group_by = state.group_by
        if group_by and group_by not in allowed_fields:
            configured_group = getattr(table_config, "group_by", None)
            group_by = configured_group if configured_group in allowed_fields else None

        # URL-driven column visibility: drop any requested hidden column that
        # is not a known/available field so the table can never be told to
        # suppress fields it does not own.
        hidden_columns = [
            name for name in (state.hidden_columns or []) if name in allowed_fields
        ]

        if (
            sort_by == state.sort_by
            and sort_order == state.sort_order
            and group_by == state.group_by
            and hidden_columns == (state.hidden_columns or [])
        ):
            return state
        return state.model_copy(
            update={
                "sort_by": sort_by,
                "sort_order": sort_order,
                "group_by": group_by,
                "hidden_columns": hidden_columns,
                "page": 1,
                "cursor": None,
            }
        )

    async def _ensure_csrf_token(self, request: Any) -> None:
        """Ensure list pages expose the token used by bulk form controls."""
        state = getattr(request, "state", None)
        if state is None or getattr(state, "csrf_token", None):
            return
        try:
            from lexigram.admin.auth.services.csrf_service import AdminCsrfService

            session = getattr(request, "scope", {}).get("session", {})
            session_id = session.get("csrf_session_id") or session.get(
                "admin_user_id", "anonymous"
            )
            state.csrf_token = AdminCsrfService(
                secret=self._config.auth.session_secret.get_secret_value()
            ).generate_token(session_id)
        except (AttributeError, TypeError, ValueError):
            # Minimal component/unit requests may not have session support;
            # the list remains renderable and middleware still fails closed.
            return

    async def render(
        self,
        request,
        resource,
        user=None,
    ) -> HTMLResponse:
        """Render list view with DataTable component."""
        await self._ensure_csrf_token(request)
        # Get resource configuration
        table_config = (
            resource.get_table_config()
            if resource and hasattr(resource, "get_table_config")
            else None
        )
        label = (
            (table_config.resource_name if table_config else self.resource_name)
            .replace("_", " ")
            .title()
        )
        admin_prefix = admin_prefix_from_request(request)
        resource_prefix = f"{admin_prefix}/{self.resource_name}"

        # Resolve Columns Early for Search
        source_columns = []
        if table_config and table_config.columns:
            source_columns = table_config.columns
        elif resource and hasattr(resource, "columns"):
            # Check if columns is a property/method
            source_columns = (
                resource.columns
                if not callable(resource.columns)
                else resource.columns()
            )

        # Parse request params using TableState
        state = TableState.from_request(
            request,
            defaults={
                "sort_by": table_config.default_sort_by if table_config else None,
                "sort_order": table_config.default_sort_order
                if table_config
                else "asc",
                "view": table_config.default_view if table_config else "tabular",
                "layout": table_config.default_layout if table_config else "stack",
                "per_page": table_config.per_page if table_config else 20,
                "density": table_config.density if table_config else "normal",
            }
            if table_config
            else {},
        )

        # Map legacy list-view aliases to a new immutable TableState. Never
        # assign onto request state directly: state is the canonical value
        # object shared by HTMX URL generation and downstream fetchers.
        legacy_sort = request.query_params.get("sort")
        # "order" is the legacy direction param emitted by older table sort
        # links (?sort=name&order=desc); "dir" is the other historical alias.
        legacy_direction = request.query_params.get("dir") or request.query_params.get(
            "order"
        )
        if legacy_sort:
            direction = (
                legacy_direction if legacy_direction in ("asc", "desc") else "asc"
            )
            state = state.model_copy(
                update={
                    "sort_by": legacy_sort,
                    "sort_order": direction,
                    "page": 1,
                    "cursor": None,
                }
            )
        elif legacy_direction in ("asc", "desc") and state.sort_by:
            state = state.model_copy(
                update={
                    "sort_order": legacy_direction,
                    "page": 1,
                    "cursor": None,
                }
            )

        # Never pass arbitrary URL field names to a resource/repository. The
        # same allowlist also keeps group-by from introspecting private or
        # unrelated record attributes during rendering.
        state = self._sanitize_table_state(
            state,
            table_config,
            source_columns,
            resource,
        )

        # Fetch data from service
        items, total = await self._fetcher.fetch_data(
            request, resource, state, source_columns
        )

        # Redact sensitive values before columns, row actions, or custom table
        # renderers can inspect the fetched records.
        request_user = getattr(getattr(request, "state", None), "user", None)
        permission_user = user if user is not None else request_user
        permission_service = self._request_permission_service(request)
        items = await self._mask_items(
            items,
            source_columns=source_columns,
            user=permission_user,
            permission_service=permission_service,
        )

        # Build columns
        columns = build_columns(source_columns, items)

        # Prepare Filters
        filter_options = get_filter_options(table_config, resource)

        # Prepare Actions
        row_actions = get_row_actions(table_config, resource, resource_prefix)

        header_actions = get_header_actions(table_config, resource)

        # Prepare Bulk Actions
        bulk_actions_list = get_bulk_actions(table_config, resource)

        # Prefer request-bound identity/permissions over an omitted handler
        # argument. The auth middleware may expose either PermissionSet or a
        # compatible mapping; normalize it once at the rendering boundary.
        request_user = getattr(getattr(request, "state", None), "user", None)
        table_permissions = self._permissions_for_request(request, user=user)

        # Prepare DataTable
        dt = DataTable(
            columns=columns,
            data=items,
            state=state,
            config=TableConfiguration(
                columns=columns,
                resource_name=self.resource_name,
                resource_prefix=resource_prefix,
                actions=row_actions,
                header_actions=header_actions,
                bulk_actions=bulk_actions_list,
                filter_options=filter_options,
                default_sort_by=state.sort_by,
                default_sort_order=state.sort_order,
                default_layout=table_config.default_layout if table_config else "stack",
                default_view=table_config.default_view if table_config else "tabular",
                group_by=state.group_by
                or (table_config.group_by if table_config else None),
                empty_state_title=(
                    table_config.empty_state_title if table_config else None
                ),
                empty_state_message=(
                    table_config.empty_state_message if table_config else None
                ),
                empty_state_icon=(
                    table_config.empty_state_icon if table_config else None
                ),
                form_display_mode=(
                    table_config.form_display_mode if table_config else "slider"
                ),
                search_fields=getattr(resource, "search_fields", None),
            ),
            total=total,
            user=user if user is not None else request_user,
            permissions=table_permissions,
            loading=False,
            error=self._fetcher.error,
            csrf_token=getattr(getattr(request, "state", None), "csrf_token", None),
        )

        is_htmx = wants_fragment(request)
        if is_htmx:
            hx_target = request.headers.get("HX-Target", "")

            # Only emit OOB control fragments for data-zone requests (search,
            # filter, paginate) where the primary swap targets #table-data and
            # toolbar elements outside the data zone need updating. Skip OOB
            # for full-zone swaps (#lexigram-table) and sidebar nav
            # (#main-content) since the primary swap replaces the entire
            # subtree, making OOB redundant.
            if hx_target == Zones.DATA.id:
                dt.props["htmx_request"] = True

            fragment_content = render_to_string(dt)
            resp_headers = {}

            # Synchronization: Force the browser URL to match the clean server-side state.
            # This removes empty params (search=&foo=) that HTMX sends via hx-include.
            # We only do this if push was not explicitly disabled in the request.
            if request.headers.get("HX-Push-Url") != "false":
                resp_headers["HX-Push-Url"] = state.to_url(resource_prefix)

            return HTMLResponse(fragment_content, headers=resp_headers)

        # Direct navigation — return full page via AdminRenderer (Jinja2 + nav population).
        # Saved views (R13): prepend the per-user views bar when available.
        saved_views_bar = await self._render_saved_views_bar(
            request, state, resource_prefix, admin_prefix
        )
        content: Any = dt
        if saved_views_bar:
            content = saved_views_bar + render_to_string(dt)
        return self._renderer.render_page(
            content,
            request=request,
            title=label,
            breadcrumbs=[
                {"label": "Dashboard", "url": admin_prefix},
                {"label": label, "url": resource_prefix},
            ],
        )

    async def _render_saved_views_bar(
        self,
        request: Any,
        state: TableState,
        resource_prefix: str,
        admin_prefix: str,
    ) -> str:
        """Render the per-user saved-views bar (R13), or ``""``.

        Reads the mount-wired service from ``request.app.state`` (the list
        renderer has no DI access at render time — doc 06). Any failure
        degrades to no bar; the list page must never break because of it.
        """
        try:
            from lexigram.admin.services.saved_views import SavedViewService

            app_state = getattr(getattr(request, "app", None), "state", None)
            service = getattr(app_state, "saved_view_service", None)
            user = getattr(getattr(request, "state", None), "user", None)
            user_id = str(getattr(user, "user_id", "") or "")
            if service is None or not user_id or user_id == "guest":
                return ""

            views = await service.list_views(user_id, self.resource_name)
            csrf_token = str(
                getattr(getattr(request, "state", None), "csrf_token", "") or ""
            )
            current_query = SavedViewService.sanitize_query(
                urlencode(state.to_query_params(exclude=["page", "cursor"]))
            )
            # Active-view matching must ignore params that merely restate the
            # resource defaults (to_query_params drops defaults for clean
            # URLs, but a saved query may spell them out explicitly).
            defaults = dict(getattr(state, "_defaults", None) or {})
            key_map = {"data_view": "view", "layout_type": "layout"}

            def _comparable(query: str) -> frozenset:
                pairs = []
                for key, value in parse_qsl(query):
                    default = defaults.get(key_map.get(key, key))
                    if default is not None and str(default) == str(value):
                        continue
                    pairs.append((key, value))
                return frozenset(pairs)

            current_params = _comparable(current_query)

            pills: list[str] = []
            for view in views:
                name = escape(view["name"])
                query = SavedViewService.sanitize_query(view["query"])
                active = bool(query) and _comparable(query) == current_params
                pill_cls = (
                    "border-primary text-primary bg-primary/5"
                    if active
                    else "border-border bg-card text-foreground"
                )
                pills.append(
                    f'<span class="inline-flex items-center rounded-full border '
                    f'{pill_cls}" data-saved-view>'
                    f'<a href="{resource_prefix}?{escape(query)}" '
                    f'class="pl-3 pr-1 py-1 text-sm hover:text-primary" '
                    f'title="Apply view">{name}</a>'
                    f'<form method="post" '
                    f'action="{admin_prefix}/views/{self.resource_name}/delete" '
                    f'class="inline-flex">'
                    f'<input type="hidden" name="csrf_token" '
                    f'value="{escape(csrf_token)}">'
                    f'<input type="hidden" name="name" value="{name}">'
                    f'<button type="submit" class="px-2 py-1 text-muted-foreground '
                    f'hover:text-destructive text-sm" title="Delete view" '
                    f'aria-label="Delete view {name}">&times;</button>'
                    f"</form></span>"
                )

            save_form = (
                f'<form method="post" '
                f'action="{admin_prefix}/views/{self.resource_name}/save" '
                f'data-saved-view-save class="inline-flex items-center gap-1.5">'
                f'<input type="hidden" name="csrf_token" '
                f'value="{escape(csrf_token)}">'
                f'<input type="hidden" name="query" '
                f'value="{escape(current_query)}">'
                f'<input type="text" name="name" required maxlength="64" '
                f'placeholder="Save current view as…" '
                f'class="rounded-lg border border-border bg-background px-2.5 '
                f'py-1 text-sm w-44">'
                f'<button type="submit" class="rounded-lg border border-border '
                f'bg-card px-2.5 py-1 text-sm font-medium hover:bg-accent">'
                f"Save view</button></form>"
            )

            return (
                '<div class="flex flex-wrap items-center gap-2 mb-4" '
                'data-saved-views>'
                '<span class="text-xs font-medium text-muted-foreground '
                'uppercase tracking-wide">Views</span>'
                + "".join(pills)
                + f'<span class="ml-auto">{save_form}</span></div>'
            )
        except Exception as exc:  # noqa: BLE001 — bar must never break the list page
            logger.warning(
                "list_renderer.saved_views_bar_failed",
                resource=self.resource_name,
                error=str(exc),
            )
            return ""


__all__ = ["ListRenderer"]
