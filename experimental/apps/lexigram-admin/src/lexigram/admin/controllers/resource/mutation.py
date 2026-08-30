"""Create/update/delete mutations for the resource controller."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar, get_args

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from lexigram.admin.exceptions import AdminValidationError, NotFoundError
from lexigram.admin.resources.form_guard import PROTECTED_FORM_FIELDS
from lexigram.admin.state.context import AdminContextManager
from lexigram.admin.ui.molecules.toast_notification import ToastNotification

if TYPE_CHECKING:
    from lexigram.admin.controllers.resource.meta import ResourceMeta


class ResourceMutationMixin:
    """Create, update, delete, restore."""

    # Host attributes provided by sibling mixins on ResourceController.
    meta: ResourceMeta
    soft_delete_enabled: bool

    render_form: Any
    render_form_partial: Any
    get_data_source: Any
    _emit_audit: Any
    _record_revision: Any

    async def create_form(self, request: Request) -> Response:
        """Show create form."""
        async with AdminContextManager(request) as ctx:
            if ctx.is_htmx:
                return HTMLResponse(self.render_form_partial(ctx, None))
            return HTMLResponse(self.render_form(ctx, None))

    async def create(self, request: Request) -> Response:
        """Create new resource."""
        async with AdminContextManager(request) as ctx:
            form_data = request.scope.get("admin_form_data")
            if form_data is None:
                form_data = await request.form()
            data = dict(form_data)

            # Validate
            try:
                validated = self.validate_create(data)
            except AdminValidationError as e:
                # Return form with errors
                if ctx.is_htmx:
                    return HTMLResponse(
                        self.render_form_partial(ctx, None, data, e.details or {}),
                        status_code=422,
                    )
                return HTMLResponse(
                    self.render_form(ctx, None, data, e.details or {}),
                    status_code=422,
                )

            # Create
            data_source = self.get_data_source()
            try:
                created = await data_source.create(validated)
            except ValueError as e:
                return HTMLResponse(str(e), status_code=400)
            created_id = str(getattr(created, "id", "") if created else "")
            await self._emit_audit(
                request,
                f"{getattr(self.meta, 'name', 'resource')}.create",
                item_id=created_id,
                new_values=validated,
            )
            await self._record_revision(
                request, created_id, validated, comment="create"
            )

            # Redirect or return success
            (
                ToastNotification.make("Created successfully")
                .success()
                .title("Saved")
                .duration(4000)
                .send()
            )
            if ctx.is_htmx:
                response = Response(status_code=200)
                response.headers["HX-Redirect"] = f"{self.meta.prefix}/{self.meta.name}"
                return response

            return RedirectResponse(
                url=f"{self.meta.prefix}/{self.meta.name}",
                status_code=302,
            )

    _PROTECTED_FIELDS: ClassVar[frozenset[str]] = PROTECTED_FORM_FIELDS

    @classmethod
    def _model_type(cls) -> type | None:
        """Extract the concrete model bound via ``ResourceController[Model]``."""
        for klass in cls.__mro__:
            for base in getattr(klass, "__orig_bases__", ()):
                args = get_args(base)
                if args and isinstance(args[0], type):
                    return args[0]
        return None

    @classmethod
    def _validated_model_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Coerce HTML form strings and guard against mass assignment.

        Delegates to the shared :func:`lexigram.admin.resources.form_guard
        .sanitize_form_data` — the same protection the live handler
        pipeline applies — so both paths cannot drift.
        """
        from lexigram.admin.resources.form_guard import sanitize_form_data

        return sanitize_form_data(
            data,
            model=cls._model_type(),
            protected_fields=cls._PROTECTED_FIELDS,
        )

    def validate_create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Coerce form values and keep only declared model fields.

        Unknown keys (potential mass-assignment vectors such as ``role`` or
        ``tenant_id``) and protected columns are stripped. Override to
        customize beyond this baseline.
        """
        return self._validated_model_fields(data)

    async def edit_form(self, request: Request) -> Response:
        """Show edit form."""
        async with AdminContextManager(request) as ctx:
            item_id = request.path_params.get("id")

            data_source = self.get_data_source()
            item = await data_source.find_one(item_id)

            if item is None:
                raise NotFoundError(message=f"{self.meta.label} not found")

            if ctx.is_htmx:
                return HTMLResponse(self.render_form_partial(ctx, item))
            return HTMLResponse(self.render_form(ctx, item))

    async def update(self, request: Request) -> Response:
        """Update existing resource."""
        async with AdminContextManager(request) as ctx:
            item_id = request.path_params.get("id")
            form_data = request.scope.get("admin_form_data")
            if form_data is None:
                form_data = await request.form()
            data = dict(form_data)

            # Validate
            try:
                validated = self.validate_update(item_id, data)
            except AdminValidationError as e:
                # Get current item for form
                item = await self.get_data_source().find_one(item_id)
                if ctx.is_htmx:
                    return HTMLResponse(
                        self.render_form_partial(ctx, item, data, e.details or {}),
                        status_code=422,
                    )
                return HTMLResponse(
                    self.render_form(ctx, item, data, e.details or {}),
                    status_code=422,
                )

            # Update
            data_source = self.get_data_source()
            item = await data_source.find_one(item_id)
            can_update = getattr(self, "can_update", None)
            if can_update and not can_update(item):
                return HTMLResponse("This record cannot be updated", status_code=403)
            try:
                item = await data_source.update(item_id, validated)
            except ValueError as e:
                return HTMLResponse(str(e), status_code=400)
            await self._emit_audit(
                request,
                f"{getattr(self.meta, 'name', 'resource')}.update",
                item_id=str(item_id),
                new_values=validated,
            )
            await self._record_revision(
                request, str(item_id), validated, comment="update"
            )

            (
                ToastNotification.make("Updated successfully")
                .success()
                .title("Saved")
                .duration(4000)
                .send()
            )
            if ctx.is_htmx:
                response = Response(status_code=200)
                response.headers["HX-Redirect"] = (
                    f"{self.meta.prefix}/{self.meta.name}/{item_id}"
                )
                return response

            return RedirectResponse(
                url=f"{self.meta.prefix}/{self.meta.name}/{item_id}",
                status_code=302,
            )

    def validate_update(self, item_id: Any, data: dict[str, Any]) -> dict[str, Any]:
        """Coerce form values and keep only declared model fields."""
        return self._validated_model_fields(data)

    async def delete_confirm(self, request: Request) -> Response:
        """Render a delete confirmation slide-over panel.

        Called via HTMX GET from the Delete row action. Returns an
        AdminSlideOver fragment that lets the user confirm or cancel
        the deletion without using the native browser confirm dialog.
        """
        item_id = request.path_params.get("id")
        label = self.meta.label

        # Attempt to fetch a human-readable label for the record
        record_label = f"{label} #{item_id}"
        try:
            data_source = self.get_data_source()
            item = await data_source.find_one(item_id)
            if item:
                for field in ("name", "title", "email", "username", "label"):
                    val = getattr(item, field, None)
                    if val:
                        record_label = str(val)
                        break
        except Exception:  # noqa: BLE001, S110
            pass

        delete_url = f"{self.meta.prefix}/{self.meta.name}/{item_id}"
        from lexigram.admin.ui.organisms.admin_slide_over import render_delete_confirm

        html = render_delete_confirm(
            record_label=record_label,
            delete_url=delete_url,
        )
        return HTMLResponse(html)

    async def delete(self, request: Request) -> Response:
        """Delete resource (soft or hard depending on soft_delete_enabled)."""
        async with AdminContextManager(request) as ctx:
            item_id = request.path_params.get("id")
            data_source = self.get_data_source()

            if self.soft_delete_enabled:
                # Soft delete — stamp deleted_at instead of removing the row
                updated = await data_source.update(
                    item_id, {"deleted_at": datetime.now(UTC).isoformat()}
                )
                if updated is None:
                    raise NotFoundError(message=f"{self.meta.label} not found")
                await self._emit_audit(
                    request,
                    f"{getattr(self.meta, 'name', 'resource')}.soft_delete",
                    item_id=str(item_id),
                )
            else:
                success = await data_source.delete(item_id)
                if not success:
                    raise NotFoundError(message=f"{self.meta.label} not found")
                await self._emit_audit(
                    request,
                    f"{getattr(self.meta, 'name', 'resource')}.delete",
                    item_id=str(item_id),
                )

            (
                ToastNotification.make("Deleted successfully")
                .success()
                .title("Deleted")
                .duration(4000)
                .send()
            )
            if ctx.is_htmx:
                response = Response(status_code=200)
                response.headers["HX-Redirect"] = f"{self.meta.prefix}/{self.meta.name}"
                return response

            return RedirectResponse(
                url=f"{self.meta.prefix}/{self.meta.name}",
                status_code=302,
            )

    async def restore(self, request: Request) -> Response:
        """Restore a soft-deleted resource (clears deleted_at).

        Only available when soft_delete_enabled is True.
        """
        async with AdminContextManager(request) as ctx:
            if not self.soft_delete_enabled:
                return HTMLResponse(
                    "Soft delete is not enabled for this resource", status_code=400
                )

            item_id = request.path_params.get("id")
            data_source = self.get_data_source()

            updated = await data_source.update(item_id, {"deleted_at": None})
            if updated is None:
                raise NotFoundError(message=f"{self.meta.label} not found")
            await self._emit_audit(
                request,
                f"{getattr(self.meta, 'name', 'resource')}.restore",
                item_id=str(item_id),
            )

            (
                ToastNotification.make("Restored successfully")
                .success()
                .title("Restored")
                .duration(4000)
                .send()
            )
            if ctx.is_htmx:
                response = Response(status_code=200)
                response.headers["HX-Trigger"] = (
                    '{"refresh-list":true,"show-toast":{"message":"Restored successfully","type":"success"}}'
                )
                return response

            return RedirectResponse(
                url=f"{self.meta.prefix}/{self.meta.name}",
                status_code=302,
            )
