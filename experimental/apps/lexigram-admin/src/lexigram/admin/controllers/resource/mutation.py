"""Create/update/delete mutations for the resource controller."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import inspect
from typing import TYPE_CHECKING, Any, ClassVar, get_args

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from lexigram.admin.exceptions import (
    AdminValidationError,
    NotFoundError,
    PermissionDeniedError,
)
from lexigram.admin.resources.form_guard import PROTECTED_FORM_FIELDS
from lexigram.admin.resources.urls import admin_prefix_from_request, admin_url
from lexigram.admin.state.context import AdminContextManager
from lexigram.admin.ui.molecules.toast_notification import ToastNotification
from lexigram.contracts.exceptions.domain import FieldError
from lexigram.logging import get_logger

logger = get_logger(__name__)

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

    def _resource_url(self, request: Request, suffix: str = "") -> str:
        """Build a URL under the request's active admin mount.

        The compatibility controller predates the mounted resource handler and
        historically used ``meta.prefix`` directly. Requests can now be served
        under a custom mount, so redirects and form actions must use the same
        request-aware URL contract as the newer resource pipeline.
        """
        scope = getattr(request, "scope", {})
        explicit_prefix = (
            scope.get("admin_prefix") if isinstance(scope, Mapping) else None
        )
        app_prefix = getattr(
            getattr(getattr(request, "app", None), "state", None),
            "admin_prefix",
            None,
        )
        configured_prefix = getattr(self.meta, "prefix", None)
        prefix = (
            admin_prefix_from_request(request)
            if explicit_prefix or (isinstance(app_prefix, str) and app_prefix)
            else (configured_prefix or admin_prefix_from_request(request))
        )
        return admin_url(prefix, getattr(self.meta, "name", ""), suffix)

    def _form_response(
        self,
        ctx: Any,
        item: Any,
        data: dict[str, Any] | None,
        errors: dict[str, list[str]],
        status_code: int = 422,
    ) -> Response:
        """Render a safe validation response for either request mode."""
        try:
            body = (
                self.render_form_partial(ctx, item, data, errors)
                if ctx.is_htmx
                else self.render_form(ctx, item, data, errors)
            )
            return HTMLResponse(body, status_code=status_code)
        except Exception:  # noqa: BLE001 — presentation hooks are extensions
            logger.exception("admin.resource_form_render_failed")
            return HTMLResponse("Unable to render form", status_code=500)

    @staticmethod
    def _record_id(record: Any) -> str:
        """Read an identifier from object- and mapping-backed records."""
        value = (
            record.get("id") if isinstance(record, dict) else getattr(record, "id", "")
        )
        return str(value) if value is not None else ""

    async def _record_permission(
        self, request: Request, name: str, item: Any = None
    ) -> bool:
        """Evaluate an optional resource-level permission hook.

        The controller is also used without the legacy ``Resource`` wrapper,
        so hooks are optional. When present they are enforced server-side in
        addition to request-level RBAC and may be synchronous or async.
        """
        checker = getattr(self, name, None)
        if not callable(checker):
            return True
        user = getattr(request.state, "user", None)
        try:
            result = checker(item) if item is not None else checker(user)
            return bool(await result) if inspect.isawaitable(result) else bool(result)
        except Exception:  # noqa: BLE001 — authorization fails closed
            return False

    async def create_form(self, request: Request) -> Response:
        """Show create form."""
        async with AdminContextManager(request) as ctx:
            if not await self._record_permission(request, "can_create"):
                return HTMLResponse("Forbidden", status_code=403)
            try:
                if ctx.is_htmx:
                    return HTMLResponse(self.render_form_partial(ctx, None))
                return HTMLResponse(self.render_form(ctx, None))
            except Exception:  # noqa: BLE001 — presentation hooks are extensions
                logger.exception("admin.resource_create_form_render_failed")
                return HTMLResponse("Unable to render form", status_code=500)

    async def create(self, request: Request) -> Response:
        """Create new resource."""
        async with AdminContextManager(request) as ctx:
            if not await self._record_permission(request, "can_create"):
                return HTMLResponse("Forbidden", status_code=403)
            try:
                form_data = request.scope.get("admin_form_data")
                if form_data is None:
                    form_data = await request.form()
                from lexigram.admin.resources.action_handlers import _form_data_dict

                data = _form_data_dict(form_data)
                data.pop("csrf_token", None)
            except Exception:  # noqa: BLE001 — malformed bodies are client errors
                logger.exception("admin.resource_create_form_parse_failed")
                return HTMLResponse("Invalid form data", status_code=400)

            from lexigram.admin.resources.action_handlers import (
                _validation_errors_to_dict,
            )

            # Validate
            try:
                validated = self.validate_create(data)
            except AdminValidationError as e:
                return self._form_response(
                    ctx, None, data, _validation_errors_to_dict(e)
                )
            except (TypeError, ValueError) as exc:
                logger.info("admin.resource_create_validation_failed", error=str(exc))
                return self._form_response(
                    ctx, None, data, {"__all__": ["Form validation failed"]}
                )
            except Exception:  # noqa: BLE001 — custom validation is an extension
                logger.exception("admin.resource_create_validation_failed")
                return HTMLResponse("Unable to validate form", status_code=500)

            # Create
            try:
                data_source = self.get_data_source()
                created_result = data_source.create(validated)
                created = (
                    await created_result
                    if inspect.isawaitable(created_result)
                    else created_result
                )
            except (PermissionError, PermissionDeniedError):
                return HTMLResponse("Forbidden", status_code=403)
            except NotImplementedError:
                return HTMLResponse("Resource does not support create", status_code=503)
            except (TypeError, ValueError):
                logger.exception("admin.resource_create_rejected")
                return self._form_response(
                    ctx, None, data, {"__all__": ["Unable to create record"]}
                )
            except Exception:  # noqa: BLE001 — storage failures are sanitized
                logger.exception("admin.resource_create_failed")
                return HTMLResponse("Unable to create record", status_code=503)
            if created is None:
                return HTMLResponse("Unable to create record", status_code=503)
            created_id = self._record_id(created)
            if not created_id:
                logger.error("admin.resource_create_missing_id")
                return HTMLResponse("Unable to create record", status_code=500)
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
                response.headers["HX-Redirect"] = self._resource_url(request)
                return response

            return RedirectResponse(
                url=self._resource_url(request),
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
        """Coerce, validate, and guard HTML form data.

        This controller is a compatibility CRUD surface, but it must apply
        the same model contract as the mounted resource handler. Sanitizing
        alone would let required fields and model constraints be bypassed.
        """
        from lexigram.admin.resources.form_guard import sanitize_form_data

        model = cls._model_type()
        protected_fields = set(cls._PROTECTED_FIELDS)
        protected_fields.update(getattr(cls, "form_exclude_fields", ()) or ())
        protected_fields.update(getattr(cls, "readonly_fields", ()) or ())
        cleaned = sanitize_form_data(
            data,
            model=model,
            protected_fields=protected_fields,
        )
        if model is None:
            return cleaned

        try:
            validator = getattr(model, "model_validate", None)
            if callable(validator):
                instance = validator(cleaned)
                if hasattr(instance, "model_dump"):
                    cleaned = {
                        key: value
                        for key, value in instance.model_dump(
                            exclude_unset=True
                        ).items()
                        if key in cleaned
                    }
            else:
                # Dataclass/domain-model compatibility for older controller
                # users. Keep the sanitized mapping on success so framework
                # fields/defaults are not accidentally sent to the data source.
                model(**cleaned)
        except (TypeError, ValueError, AttributeError) as exc:
            errors: list[FieldError] = []
            raw_errors = getattr(exc, "errors", None)
            if callable(raw_errors):
                for error in raw_errors():
                    location = error.get("loc", ())
                    field = str(location[0]) if location else "__all__"
                    errors.append(
                        FieldError(field=field, message=str(error.get("msg", exc)))
                    )
            if not errors:
                errors.append(FieldError(field="__all__", message=str(exc)))
            raise AdminValidationError(
                message="Form validation failed",
                errors=errors,
            ) from exc

        return cleaned

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

            try:
                data_source = self.get_data_source()
                lookup = data_source.find_one(item_id)
                item = await lookup if inspect.isawaitable(lookup) else lookup
            except NotImplementedError:
                return HTMLResponse("Resource data source unavailable", status_code=503)
            except Exception:  # noqa: BLE001 — storage failures are sanitized
                logger.exception("admin.resource_edit_lookup_failed")
                return HTMLResponse("Unable to load record", status_code=503)

            if item is None:
                raise NotFoundError(message=f"{self.meta.label} not found")
            if not await self._record_permission(request, "can_update", item):
                return HTMLResponse("Forbidden", status_code=403)

            try:
                if ctx.is_htmx:
                    return HTMLResponse(self.render_form_partial(ctx, item))
                return HTMLResponse(self.render_form(ctx, item))
            except Exception:  # noqa: BLE001 — presentation hooks are extensions
                logger.exception("admin.resource_edit_form_render_failed")
                return HTMLResponse("Unable to render form", status_code=500)

    @staticmethod
    def _record_mapping(item: Any) -> dict[str, Any]:
        """Normalize persisted records before validating a partial edit."""
        if isinstance(item, dict):
            return dict(item)
        model_dump = getattr(item, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump()
            if isinstance(dumped, dict):
                return dumped
        try:
            values = vars(item)
        except TypeError:
            return {}
        return dict(values) if isinstance(values, dict) else {}

    async def update(self, request: Request) -> Response:
        """Update existing resource."""
        async with AdminContextManager(request) as ctx:
            item_id = request.path_params.get("id")
            try:
                form_data = request.scope.get("admin_form_data")
                if form_data is None:
                    form_data = await request.form()
                from lexigram.admin.resources.action_handlers import _form_data_dict

                data = _form_data_dict(form_data)
                data.pop("csrf_token", None)
            except Exception:  # noqa: BLE001 — malformed bodies are client errors
                logger.exception("admin.resource_update_form_parse_failed")
                return HTMLResponse("Invalid form data", status_code=400)

            from lexigram.admin.resources.action_handlers import (
                _validation_errors_to_dict,
            )

            # Fetch before validation so a partial edit can be validated
            # against the persisted record. Disabled/readonly controls are
            # intentionally absent from browser submissions.
            try:
                data_source = self.get_data_source()
                lookup = data_source.find_one(item_id)
                item = await lookup if inspect.isawaitable(lookup) else lookup
            except NotImplementedError:
                return HTMLResponse("Resource data source unavailable", status_code=503)
            except Exception:  # noqa: BLE001 — storage failures are sanitized
                logger.exception("admin.resource_update_lookup_failed")
                return HTMLResponse("Unable to load record", status_code=503)
            if item is None:
                raise NotFoundError(message=f"{self.meta.label} not found")
            if not await self._record_permission(request, "can_update", item):
                return HTMLResponse("This record cannot be updated", status_code=403)

            # Validate
            try:
                validated = self.validate_update(
                    item_id, {**self._record_mapping(item), **data}
                )
            except AdminValidationError as e:
                return self._form_response(
                    ctx, item, data, _validation_errors_to_dict(e)
                )
            except (TypeError, ValueError) as exc:
                logger.info("admin.resource_update_validation_failed", error=str(exc))
                return self._form_response(
                    ctx, item, data, {"__all__": ["Form validation failed"]}
                )
            except Exception:  # noqa: BLE001 — custom validation is an extension
                logger.exception("admin.resource_update_validation_failed")
                return HTMLResponse("Unable to validate form", status_code=500)

            # Update
            try:
                update_result = data_source.update(item_id, validated)
                item = (
                    await update_result
                    if inspect.isawaitable(update_result)
                    else update_result
                )
            except (PermissionError, PermissionDeniedError):
                return HTMLResponse("Forbidden", status_code=403)
            except NotImplementedError:
                return HTMLResponse("Resource does not support update", status_code=503)
            except (TypeError, ValueError):
                logger.exception("admin.resource_update_rejected")
                return self._form_response(
                    ctx, item, data, {"__all__": ["Unable to update record"]}
                )
            except Exception:  # noqa: BLE001 — storage failures are sanitized
                logger.exception("admin.resource_update_failed")
                return HTMLResponse("Unable to update record", status_code=503)
            # Compatibility data sources may perform an update without
            # returning the refreshed record; the preflight lookup above still
            # established that the target existed.
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
                response.headers["HX-Redirect"] = self._resource_url(
                    request, str(item_id)
                )
                return response

            return RedirectResponse(
                url=self._resource_url(request, str(item_id)),
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
            lookup = data_source.find_one(item_id)
            item = await lookup if inspect.isawaitable(lookup) else lookup
        except NotImplementedError:
            return HTMLResponse("Resource data source unavailable", status_code=503)
        except Exception:  # noqa: BLE001 — storage failures are sanitized
            logger.exception("admin.resource_delete_confirm_lookup_failed")
            return HTMLResponse("Unable to load record", status_code=503)

        if item is None:
            raise NotFoundError(message=f"{self.meta.label} not found")
        if not await self._record_permission(request, "can_delete", item):
            return HTMLResponse("Forbidden", status_code=403)
        for field in ("name", "title", "email", "username", "label"):
            val = (
                item.get(field)
                if isinstance(item, dict)
                else getattr(item, field, None)
            )
            if val:
                record_label = str(val)
                break

        delete_url = self._resource_url(request, str(item_id))
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
            try:
                data_source = self.get_data_source()
                lookup = data_source.find_one(item_id)
                item = await lookup if inspect.isawaitable(lookup) else lookup
            except NotImplementedError:
                return HTMLResponse("Resource data source unavailable", status_code=503)
            except Exception:  # noqa: BLE001 — storage failures are sanitized
                logger.exception("admin.resource_delete_lookup_failed")
                return HTMLResponse("Unable to load record", status_code=503)
            if item is None:
                raise NotFoundError(message=f"{self.meta.label} not found")
            if not await self._record_permission(request, "can_delete", item):
                return HTMLResponse("This record cannot be deleted", status_code=403)

            try:
                if self.soft_delete_enabled:
                    # Soft delete — stamp deleted_at instead of removing the row
                    update_result = data_source.update(
                        item_id, {"deleted_at": datetime.now(UTC).isoformat()}
                    )
                    updated = (
                        await update_result
                        if inspect.isawaitable(update_result)
                        else update_result
                    )
                    if updated is None:
                        raise NotFoundError(message=f"{self.meta.label} not found")
                    await self._emit_audit(
                        request,
                        f"{getattr(self.meta, 'name', 'resource')}.soft_delete",
                        item_id=str(item_id),
                    )
                else:
                    delete_result = data_source.delete(item_id)
                    success = (
                        await delete_result
                        if inspect.isawaitable(delete_result)
                        else delete_result
                    )
                    if not success:
                        raise NotFoundError(message=f"{self.meta.label} not found")
                    await self._emit_audit(
                        request,
                        f"{getattr(self.meta, 'name', 'resource')}.delete",
                        item_id=str(item_id),
                    )
            except NotFoundError:
                raise
            except (PermissionError, PermissionDeniedError):
                return HTMLResponse("Forbidden", status_code=403)
            except NotImplementedError:
                return HTMLResponse("Resource does not support delete", status_code=503)
            except Exception:  # noqa: BLE001 — storage/audit failures are sanitized
                logger.exception("admin.resource_delete_failed")
                return HTMLResponse("Unable to delete record", status_code=503)

            (
                ToastNotification.make("Deleted successfully")
                .success()
                .title("Deleted")
                .duration(4000)
                .send()
            )
            if ctx.is_htmx:
                response = Response(status_code=200)
                response.headers["HX-Redirect"] = self._resource_url(request)
                return response

            return RedirectResponse(
                url=self._resource_url(request),
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
            try:
                data_source = self.get_data_source()
                lookup = data_source.find_one(item_id)
                item = await lookup if inspect.isawaitable(lookup) else lookup
            except NotImplementedError:
                return HTMLResponse("Resource data source unavailable", status_code=503)
            except Exception:  # noqa: BLE001 — storage failures are sanitized
                logger.exception("admin.resource_restore_lookup_failed")
                return HTMLResponse("Unable to load record", status_code=503)
            if item is None:
                raise NotFoundError(message=f"{self.meta.label} not found")
            if not await self._record_permission(request, "can_update", item):
                return HTMLResponse("This record cannot be restored", status_code=403)

            try:
                update_result = data_source.update(item_id, {"deleted_at": None})
                updated = (
                    await update_result
                    if inspect.isawaitable(update_result)
                    else update_result
                )
            except (PermissionError, PermissionDeniedError):
                return HTMLResponse("Forbidden", status_code=403)
            except NotImplementedError:
                return HTMLResponse(
                    "Resource does not support restore", status_code=503
                )
            except Exception:  # noqa: BLE001 — storage failures are sanitized
                logger.exception("admin.resource_restore_failed")
                return HTMLResponse("Unable to restore record", status_code=503)
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
                url=self._resource_url(request),
                status_code=302,
            )
