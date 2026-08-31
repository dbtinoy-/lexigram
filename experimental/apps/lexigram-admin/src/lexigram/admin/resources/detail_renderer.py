from __future__ import annotations

"""Detail view rendering for admin resources."""

import inspect
from typing import Any

from starlette.responses import HTMLResponse

from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.exceptions import DataError
from lexigram.admin.observability.admin_metrics import AdminMetrics, OperationTimer
from lexigram.admin.resources.form_guard import PROTECTED_FORM_FIELDS
from lexigram.admin.resources.urls import admin_prefix_from_request
from lexigram.admin.state.context import wants_fragment
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str
from lexigram.ui import InfolistWidget, el, raw, render_to_string

logger = get_logger(__name__)
_MASKED_FIELD_VALUE = "[REDACTED]"


@inject
class DetailRenderer:
    """Handles rendering of detail views for admin resources."""

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

    @staticmethod
    def _field_schemas(resource: Any) -> dict[str, Any]:
        """Resolve the fields that are explicitly safe for detail rendering."""
        declared = getattr(resource, "fields", None)
        if declared:
            return {
                str(field.name): field
                for field in declared
                if getattr(field, "name", None)
            }

        model = getattr(resource, "model", None)
        if model is None:
            # Do not infer a detail allow-list from arbitrary record keys. A
            # data source may contain secrets that were never intended for UI.
            return {}
        try:
            from lexigram.admin.forms.components import FormSchemaGenerator

            schema = FormSchemaGenerator().from_pydantic(model)
            return {field.name: field for field in schema.fields}
        except (ImportError, AttributeError, TypeError, ValueError):
            return {}

    @staticmethod
    def _permission_service(request: Any) -> Any | None:
        """Resolve the mounted field-permission service, if available."""
        try:
            app = request.app
        except (AttributeError, KeyError):
            app = None
        service = getattr(getattr(app, "state", None), "permission_service", None)
        if service is not None and callable(getattr(service, "can_view_field", None)):
            return service
        try:
            state = request.state
        except (AttributeError, KeyError):
            state = None
        service = getattr(state, "permission_service", None)
        return (
            service
            if service is not None and callable(getattr(service, "can_view_field", None))
            else None
        )

    async def _field_visible(
        self,
        request: Any,
        user: Any,
        permission_service: Any | None,
        field_name: str,
    ) -> bool:
        """Check field visibility for the inline detail contract."""
        if user is None or permission_service is None:
            return True
        try:
            result = permission_service.can_view_field(
                user, self.resource_name, field_name
            )
            if inspect.isawaitable(result):
                result = await result
            return bool(result)
        except Exception:  # noqa: BLE001 — field access must fail closed
            logger.exception(
                "admin.inline_field_visibility_check_failed",
                resource=self.resource_name,
                field=field_name,
            )
            return False

    async def _field_masked(
        self,
        user: Any,
        permission_service: Any | None,
        field_name: str,
    ) -> bool:
        """Check whether a field value must be redacted for this viewer."""
        checker = getattr(permission_service, "should_mask_field", None)
        if not callable(checker):
            return False
        try:
            result = checker(user, self.resource_name, field_name)
            if inspect.isawaitable(result):
                result = await result
            return bool(result)
        except Exception:  # noqa: BLE001 — masking must fail closed
            logger.exception(
                "admin.field_mask_check_failed",
                resource=self.resource_name,
                field=field_name,
            )
            return True

    async def _can_edit_record(
        self,
        request: Any,
        resource: Any,
        user: Any,
    ) -> bool:
        """Resolve the same update capability used by the route guard."""
        try:
            capabilities = getattr(request.state, "permissions", None)
        except (AttributeError, KeyError):
            capabilities = None
        if isinstance(capabilities, dict) and "can_update" in capabilities:
            return bool(capabilities["can_update"])

        checker = getattr(resource, "has_change_permission", None)
        if not callable(checker):
            return True
        try:
            result = checker(user)
            if inspect.isawaitable(result):
                result = await result
            return bool(result)
        except Exception:  # noqa: BLE001 — a broken permission hook hides the action
            logger.exception("admin.detail_edit_permission_check_failed")
            return False

    async def render_detail(
        self,
        request,
        resource,
        item_id: str,
        user=None,
    ) -> HTMLResponse:
        """Render detail view."""
        timer = OperationTimer()

        label = self.resource_name.replace("_", " ").title()

        request_user = user
        if request_user is None:
            request_user = getattr(getattr(request, "state", None), "user", None)
        item_html = await self._get_item_html(
            resource,
            item_id,
            label,
            request=request,
            user=request_user,
        )
        show_edit = await self._can_edit_record(request, resource, request_user)

        prefix = admin_prefix_from_request(request)
        resource_url = f"{prefix}/{self.resource_name}"
        detail_url = f"{resource_url}/{item_id}"
        content = render_to_string(
            el(
                "div",
                el(
                    "div",
                    el(
                        "a",
                        f"← Back to {label}",
                        href=resource_url,
                        style="color: #6366f1;",
                    ),
                    el("h1", f"{label} #{item_id}"),
                    style="margin-bottom: 1.5rem;",
                    class_="resource-header",
                ),
                el(
                    "div",
                    raw(item_html),
                    class_="resource-content",
                ),
                (
                    el(
                        "div",
                        el(
                            "a",
                            "Edit",
                            href=f"{detail_url}/edit",
                            class_="btn btn-secondary",
                        ),
                        style="margin-top: 1rem;",
                        class_="resource-actions",
                    )
                    if show_edit
                    else ""
                ),
            )
        )

        is_htmx = wants_fragment(request)
        if is_htmx:
            self._metrics.record_operation(
                "detail",
                resource=self.resource_name,
                status="success",
                duration_seconds=timer.elapsed(),
            )
            return HTMLResponse(content)

        self._metrics.record_operation(
            "detail",
            resource=self.resource_name,
            status="success",
            duration_seconds=timer.elapsed(),
        )

        return self._renderer.render_page(
            content,
            request=request,
            title=f"{label} #{item_id}",
            breadcrumbs=[
                {"label": "Dashboard", "url": prefix},
                {"label": label, "url": resource_url},
                {
                    "label": f"#{item_id}",
                    "url": detail_url,
                },
            ],
        )

    async def render_inline_edit(
        self,
        request,
        resource,
        item_id: str,
        user=None,
    ) -> HTMLResponse:
        """Render detail view with inline editable fields.

        Each field is rendered as an Alpine.js-driven inline editor.  In
        *display* mode the current value is shown with a pencil icon that
        appears on hover.  Clicking the icon switches to *edit* mode which
        shows an ``<input>`` alongside Save and Cancel buttons.  Saving
        issues an HTMX ``PATCH`` to
        ``/{resource_name}/{item_id}/inline?field=<name>`` carrying the new
        value.

        Args:
            request: Incoming HTTP request.
            resource: Admin resource instance.
            item_id: Primary-key value of the record to display.
            user: Authenticated user (optional, for future RBAC use).

        Returns:
            ``HTMLResponse`` with the inline-edit fragment or full page.
        """
        label = self.resource_name.replace("_", " ").title()
        item_dict: dict = {}

        if resource:
            try:
                from lexigram.admin.resources.data_access import get_resource_data_source

                data_source = get_resource_data_source(resource)
                getter = getattr(data_source, "find_one", None)
                if getter is not None:
                    item = await getter(item_id)
                    if item:
                        item_dict = (
                            dict(item)
                            if isinstance(item, dict)
                            else item.model_dump()
                            if hasattr(item, "model_dump")
                            else dict(vars(item))
                        )
            except DataError as exc:
                logger.debug(
                    "inline_edit fetch failed resource=%s id=%s: %s",
                    self.resource_name,
                    item_id,
                    exc,
                )
                raise DataError(
                    message=f"Failed to retrieve {self.resource_name} item {item_id}",
                    original_error=exc,
                ) from None

        prefix = admin_prefix_from_request(request)
        patch_base = f"{prefix}/{self.resource_name}/{item_id}/inline"
        csrf_token = getattr(getattr(request, "state", None), "csrf_token", None)
        csrf_attrs = (
            {"hx_headers": dumps_str({"X-CSRF-Token": csrf_token})}
            if csrf_token
            else {}
        )
        protected_fields = set(PROTECTED_FORM_FIELDS)
        protected_fields.update(getattr(resource, "form_exclude_fields", ()) or ())
        protected_fields.update(getattr(resource, "readonly_fields", ()) or ())
        field_schemas = self._field_schemas(resource)
        permission_service = self._permission_service(request)

        field_rows: list[Any] = []
        for field_name, field_value in item_dict.items():
            field_schema = field_schemas.get(field_name)
            if field_schema is None or not getattr(field_schema, "visible_in_view", True):
                continue
            if not await self._field_visible(
                request,
                user,
                permission_service,
                field_name,
            ):
                continue
            masked = await self._field_masked(
                user,
                permission_service,
                field_name,
            )
            display_value = _MASKED_FIELD_VALUE if masked else field_value
            alpine_key = f"editing_{field_name}"
            editable = bool(
                not masked
                and field_name not in protected_fields
                and getattr(field_schema, "visible_in_form", True)
                and not getattr(field_schema, "readonly", False)
            )
            edit_checker = getattr(permission_service, "can_edit_field", None)
            if editable and user is not None and callable(edit_checker):
                try:
                    edit_result = edit_checker(user, self.resource_name, field_name)
                    if inspect.isawaitable(edit_result):
                        edit_result = await edit_result
                    editable = bool(edit_result)
                except Exception:  # noqa: BLE001 — edit access must fail closed
                    logger.exception(
                        "admin.inline_field_edit_check_failed",
                        resource=self.resource_name,
                        field=field_name,
                    )
                    editable = False
            row = el(
                "tr",
                el(
                    "td",
                    el("strong", field_name),
                    class_="py-2 pr-4 align-top text-sm font-medium text-muted-foreground w-1/4",
                ),
                el(
                    "td",
                    # Display mode
                    el(
                        "div",
                        el(
                            "span",
                            str(display_value),
                            class_="inline-edit-value",
                        ),
                        (
                            el(
                                "button",
                                "✎",
                                type="button",
                                title=f"Edit {field_name}",
                                class_=(
                                    "inline-edit-pencil ml-2 text-primary-500 opacity-0 "
                                    "group-hover:opacity-100 transition-opacity text-xs"
                                ),
                                **{"@click": f"{alpine_key} = true"},
                            )
                            if editable
                            else ""
                        ),
                        class_="group flex items-center",
                        **{"x-show": f"!{alpine_key}"},
                    ),
                    # Edit mode
                    (
                        el(
                            "div",
                            el(
                                "input",
                                type="text",
                                name=field_name,
                                value=str(display_value),
                                class_=(
                                    "inline-edit-input border border-border "
                                    "rounded px-2 py-1 text-sm w-full "
                                    "bg-muted text-foreground "
                                    "focus:outline-none focus:ring-2 focus:ring-primary-500"
                                ),
                                **{
                                    ":name": f"'{field_name}'",
                                    "x-ref": f"input_{field_name}",
                                },
                            ),
                            el(
                                "button",
                                "Save",
                                type="button",
                                class_=(
                                    "ml-2 px-2 py-1 text-xs font-medium text-white "
                                    "bg-primary-600 hover:bg-primary-700 rounded "
                                    "focus:outline-none focus:ring-2 focus:ring-primary-500"
                                ),
                                **{
                                    "hx-patch": patch_base,
                                    "hx-include": f"[name='{field_name}']",
                                    "hx-target": "closest tr",
                                    "hx-swap": "outerHTML",
                                    "@click": f"{alpine_key} = false",
                                    **csrf_attrs,
                                },
                            ),
                            el(
                                "button",
                                "Cancel",
                                type="button",
                                class_=(
                                    "ml-1 px-2 py-1 text-xs font-medium text-muted-foreground "
                                    "dark:text-muted-foreground hover:text-foreground rounded border "
                                    "border-border"
                                ),
                                **{"@click": f"{alpine_key} = false"},
                            ),
                            class_="flex items-center gap-1",
                            **{"x-show": alpine_key},
                        )
                        if editable
                        else ""
                    ),
                    class_="py-2 text-sm text-foreground",
                ),
                **{
                    "x-data": f"{{ {alpine_key}: false }}",
                    "class": "border-t border-border",
                },
            )
            field_rows.append(row)

        table_html = render_to_string(
            el("table", *field_rows, class_="detail-inline-edit-table w-full")
        )

        resource_url = f"{prefix}/{self.resource_name}"
        detail_url = f"{resource_url}/{item_id}"
        content = render_to_string(
            el(
                "div",
                el(
                    "div",
                    el(
                        "a",
                        f"← Back to {label}",
                        href=resource_url,
                        style="color: #6366f1;",
                    ),
                    el(
                        "h1",
                        f"{label} #{item_id} ",
                        el(
                            "span",
                            "(inline edit)",
                            class_="text-muted-foreground text-xs",
                        ),
                    ),
                    style="margin-bottom: 1.5rem;",
                    class_="resource-header",
                ),
                el(
                    "div",
                    raw(table_html),
                    class_="resource-content",
                ),
            )
        )

        is_htmx = wants_fragment(request)
        if is_htmx:
            return HTMLResponse(content)

        return self._renderer.render_page(
            content,
            request=request,
            title=f"{label} #{item_id} — Inline Edit",
            breadcrumbs=[
                {"label": "Dashboard", "url": prefix},
                {"label": label, "url": resource_url},
                {
                    "label": f"#{item_id}",
                    "url": detail_url,
                },
                {
                    "label": "Inline Edit",
                    "url": f"{detail_url}/inline-edit",
                },
            ],
        )

    async def _get_item_html(
        self,
        resource,
        item_id: str,
        label: str,
        *,
        request: Any | None = None,
        user: Any = None,
    ) -> str:
        """Get HTML representation of the item."""
        if not resource:
            return render_to_string(el("p", f"Item #{item_id}"))

        item = None
        # Resolve the canonical source first. This keeps detail and inline
        # editing consistent with list/forms when a resource still exposes a
        # legacy service alongside a mounted modern source.
        from lexigram.admin.resources.data_access import get_resource_data_source

        data_source = get_resource_data_source(resource)
        if data_source is not None and hasattr(data_source, "find_one"):
            try:
                item = await data_source.find_one(item_id)
            except (AttributeError, TypeError, ValueError, KeyError, DataError) as exc:
                logger.debug(
                    "Failed to get item %s/%s via data source: %s",
                    self.resource_name,
                    item_id,
                    exc,
                )

        if item:
            item_dict = (
                dict(item)
                if isinstance(item, dict)
                else item.model_dump()
                if hasattr(item, "model_dump")
                else dict(vars(item))
            )
            return await self._render_item_infolist(
                resource,
                item_dict,
                request=request,
                user=user,
            )
        return render_to_string(el("p", "Item not found"))

    async def _render_item_infolist(
        self,
        resource,
        item_dict: dict,
        *,
        request: Any | None = None,
        user: Any = None,
    ) -> str:
        """Render item fields as an infolist widget.

        Prefers the resource's ``infolist()`` API when available
        (``HasInfolist`` mixin); otherwise derives entries from the
        resource model. Falls back to a plain key/value table when the
        resource model cannot be introspected. Field visibility and masking
        are applied before any infolist implementation receives the data.
        """
        permission_service = self._permission_service(request)
        safe_item = dict(item_dict)
        for field_name in list(safe_item):
            field_schema = self._field_schemas(resource).get(field_name)
            if field_schema is None:
                continue
            if not await self._field_visible(
                request,
                user,
                permission_service,
                field_name,
            ):
                safe_item.pop(field_name, None)
                continue
            if await self._field_masked(user, permission_service, field_name):
                safe_item[field_name] = _MASKED_FIELD_VALUE
        item_dict = safe_item

        try:
            if hasattr(resource, "infolist"):
                entries = resource.infolist(item_dict)
            else:
                from lexigram.admin.forms.components import FormSchemaGenerator

                schema = FormSchemaGenerator().from_pydantic(resource.model)
                entries = [
                    field.render_infolist_entry(item_dict[field.name])
                    for field in schema.fields
                    if field.visible_in_view and field.name in item_dict
                ]
            return render_to_string(InfolistWidget(entries=entries, columns=2).render())
        except (ImportError, AttributeError, TypeError, ValueError) as exc:
            logger.debug(
                "infolist render failed for %s: %s",
                self.resource_name,
                exc,
            )
            safe_names = set(self._field_schemas(resource))
            rows = [
                el("tr", el("td", el("strong", key)), el("td", str(value)))
                for key, value in item_dict.items()
                if key in safe_names
            ]
            if not rows:
                return render_to_string(
                    el("p", "No detail fields are configured.", class_="text-muted")
                )
            return render_to_string(el("table", *rows, class_="detail-table"))


__all__ = ["DetailRenderer"]
