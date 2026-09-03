from __future__ import annotations

import asyncio
from collections.abc import Mapping
import inspect
import secrets
from typing import Any

from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse, RedirectResponse, Response

from lexigram.admin.config import AdminConfig
from lexigram.admin.exceptions import PermissionDeniedError
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str

logger = get_logger(__name__)

# Large mutating selections are handed to the in-process progress task so the
# request can return while the same row-isolated operation continues. Keep the
# fallback threshold conservative: callers without an SSE-capable tracker stay
# on the synchronous path.
BULK_PROGRESS_THRESHOLD = 20


async def _maybe_await(value: Any) -> Any:
    """Resolve sync and async action hooks uniformly."""
    return await value if inspect.isawaitable(value) else value


from lexigram.admin.resources.action_handlers import (
    CloneActionHandler,
    CreateActionHandler,
    DeleteActionHandler,
    DetailActionHandler,
    EditActionHandler,
    ImportActionHandler,
    InlineMutationActionHandler,
    ListActionHandler,
    PurgeActionHandler,
    RelationOptionsActionHandler,
    ResourceActionHandler,
    RestoreActionHandler,
)
from lexigram.admin.resources.bulk_outcome import BulkOutcome
from lexigram.admin.resources.data_access import get_resource_data_source
from lexigram.admin.resources.urls import (
    admin_prefix_from_request,
    admin_url,
)
from lexigram.ui import el, render_to_string


class UserPermissionsActionHandler:
    """Handler for the per-user direct permission editing page (users only)."""

    def __init__(self, config: AdminConfig) -> None:
        """Initialize the handler.

        Args:
            config: Admin configuration (used for the CSRF secret).
        """
        self._config = config

    def can_handle(self, action: str) -> bool:
        """Whether this handler serves the given route action."""
        return action == "permissions"

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        """Serve GET (form) and POST (save) for user permissions.

        Only :class:`~lexigram.admin.resources.users.UserResource`
        instances support the page; other resources get a 404.
        """
        from lexigram.admin.resources.users import UserResource

        if not isinstance(resource, UserResource):
            return HTMLResponse(
                "<h1>Permissions not supported for this resource</h1>",
                status_code=404,
            )
        item_id = request.path_params.get("id", "?")
        data_source = get_resource_data_source(resource)
        if data_source is None:
            return HTMLResponse("Permissions not available", status_code=400)

        if request.method == "POST":
            return await self._handle_submit(request, resource, data_source, item_id)
        return await self._handle_form(request, resource, data_source, item_id)

    async def _handle_form(
        self,
        request: StarletteRequest,
        resource: Any,
        data_source: Any,
        item_id: str,
    ) -> Any:
        """Render the permission checkboxes for one user."""
        try:
            user = await data_source.find_one(item_id)
        except Exception as exc:  # noqa: BLE001 — storage details stay private
            logger.exception("admin.user_permissions_lookup_failed", error=str(exc))
            return HTMLResponse("Unable to load user", status_code=503)
        if user is None:
            return HTMLResponse("<h1>User not found</h1>", status_code=404)

        self._ensure_csrf_token(request)

        from lexigram.admin.resources.permissions_renderer import (
            UserPermissionsRenderer,
        )

        renderer = UserPermissionsRenderer(resource_name=resource.name or "")
        return renderer.render_form(
            request=request,
            user=user,
            inventory=self._permission_inventory(resource),
            item_id=item_id,
        )

    async def _handle_submit(
        self,
        request: StarletteRequest,
        resource: Any,
        data_source: Any,
        item_id: str,
    ) -> Any:
        """Persist the submitted direct permissions for one user."""
        try:
            form = request.scope.get("admin_form_data") or await request.form()
            getlist = getattr(form, "getlist", None)
            if callable(getlist):
                raw_permissions = getlist("permissions")
            else:
                raw_value: Any = form.get("permissions", [])
                raw_permissions = (
                    raw_value
                    if isinstance(raw_value, (list, tuple, set))
                    else [raw_value]
                )
            permissions = sorted(
                {str(v).strip() for v in raw_permissions if str(v).strip()}
            )
        except (RuntimeError, ValueError, OSError, TypeError):
            return HTMLResponse("Invalid form submission", status_code=400)

        try:
            user = await data_source.find_one(item_id)
        except Exception as exc:  # noqa: BLE001 — storage details stay private
            logger.exception("admin.user_permissions_lookup_failed", error=str(exc))
            return HTMLResponse("Unable to load user", status_code=503)
        if user is None:
            from urllib.parse import quote

            return RedirectResponse(
                url=admin_url(
                    admin_prefix_from_request(request),
                    resource.name or "",
                    suffix="",
                    query=f"error={quote('User not found.')}",
                ),
                status_code=302,
            )

        # Only inventory-backed permissions may be introduced by this form.
        # Existing custom permissions are preserved when the renderer emitted
        # them as hidden fields, but an attacker cannot add an arbitrary new
        # capability by posting a made-up string.
        try:
            inventory = self._permission_inventory(resource)
            known_permissions = {
                str(permission)
                for values in (inventory.options() or {}).values()
                for permission in values
            }
        except Exception as exc:  # noqa: BLE001 — malformed inventory is unavailable
            logger.exception("admin.user_permissions_inventory_failed", error=str(exc))
            return HTMLResponse("Permissions are unavailable", status_code=503)
        existing_permissions = {
            str(permission)
            for permission in (
                user.get("permissions", [])
                if isinstance(user, dict)
                else getattr(user, "permissions", None) or []
            )
        }
        permissions = sorted(
            permission
            for permission in permissions
            if permission in known_permissions or permission in existing_permissions
        )

        can_update = getattr(resource, "can_update", None)
        if callable(can_update):
            try:
                allowed = await _maybe_await(can_update(user))
            except Exception:  # noqa: BLE001 — authorization fails closed
                logger.exception("admin.user_permissions_authorization_failed")
                allowed = False
            if not allowed:
                return HTMLResponse("Forbidden", status_code=403)

        try:
            changed = await _maybe_await(
                resource.before_update(item_id, {"permissions": permissions})
            )
        except (PermissionError, PermissionDeniedError):
            return HTMLResponse("Forbidden", status_code=403)
        except (TypeError, ValueError):
            return HTMLResponse("Invalid permissions", status_code=422)
        except Exception:  # noqa: BLE001 — hook/storage details stay private
            logger.exception("admin.user_permissions_before_update_failed")
            return HTMLResponse("Unable to update permissions", status_code=503)
        if not isinstance(changed, dict):
            changed = {"permissions": permissions}
        # The permissions page may only update its own field, even if a
        # resource hook returns additional keys. Reapply the inventory boundary
        # after the hook so a custom hook cannot turn this scoped form into a
        # general permission write surface.
        changed_permissions = changed.get("permissions", permissions)
        if isinstance(changed_permissions, str):
            changed_permissions = [changed_permissions]
        if not isinstance(changed_permissions, (list, tuple, set)):
            changed_permissions = permissions
        persisted_permissions = sorted(
            {
                str(permission).strip()
                for permission in changed_permissions
                if str(permission).strip()
                and (
                    str(permission).strip() in known_permissions
                    or str(permission).strip() in existing_permissions
                )
            }
        )
        try:
            updated = await data_source.update(
                item_id,
                {"permissions": persisted_permissions},
            )
        except NotImplementedError:
            return HTMLResponse("Permissions are unavailable", status_code=503)
        except Exception as exc:  # noqa: BLE001 — storage details stay private
            logger.exception("admin.user_permissions_update_failed", error=str(exc))
            return HTMLResponse("Unable to update permissions", status_code=503)
        if updated is None:
            return HTMLResponse("User not found", status_code=404)
        try:
            await _maybe_await(resource.after_update(updated))
        except Exception:  # noqa: BLE001 — permission update is already persisted
            logger.exception("admin.user_permissions_after_update_failed")
            return HTMLResponse(
                "Permissions updated, but finalization failed", status_code=500
            )
        return RedirectResponse(
            url=admin_url(
                admin_prefix_from_request(request),
                resource.name or "",
                query="notice=User permissions updated.",
            ),
            status_code=302,
        )

    def _permission_inventory(self, resource: Any) -> Any:
        """Return the grouped permission inventory for the form.

        Uses the inventory wired onto the resource at mount time; falls
        back to a local inventory scoped to the resource's own name.
        """
        inventory = getattr(resource, "permission_inventory", None)
        if inventory is not None:
            return inventory
        from lexigram.admin.rbac.inventory import PermissionInventoryService

        logger.debug(
            "admin.user_permissions_inventory_fallback",
            resource=resource.name,
        )
        fallback = PermissionInventoryService()
        fallback.register_resources([resource.name or "users"])
        return fallback

    def _ensure_csrf_token(self, request: StarletteRequest) -> None:
        """Ensure ``request.state.csrf_token`` exists for the form embed."""
        if getattr(getattr(request, "state", None), "csrf_token", None):
            return
        from lexigram.admin.auth.services.csrf_service import AdminCsrfService

        session = getattr(request, "session", {})
        session_id = session.get("csrf_session_id") or session.get(
            "admin_user_id", "anonymous"
        )
        request.state.csrf_token = AdminCsrfService(
            secret=self._config.auth.session_secret.get_secret_value()
        ).generate_token(session_id)


class BulkActionHandler:
    """Handler for the ``bulk`` action — processes bulk operations."""

    _MAX_SELECTED_IDS = 1000
    #: Hard caps for id-less "export the filtered view" requests (R25).
    _MAX_FILTERED_EXPORT_ROWS = 10_000
    _FILTERED_EXPORT_PAGE_SIZE = 1000
    _MAX_LIST_QUERY_LENGTH = 4096
    _CONFIRM_LABELS = {
        "bulk-delete-confirm": ("delete", "Delete", "DELETE"),
        "bulk-purge-confirm": ("purge", "Purge", "PURGE"),
        "bulk-restore-confirm": ("restore", "Restore", "RESTORE"),
    }
    # Public on the handler as well as module-level so an application/test can
    # tune the rollout without changing the endpoint contract.
    BULK_PROGRESS_THRESHOLD = BULK_PROGRESS_THRESHOLD

    def __init__(self) -> None:
        # A task must be strongly referenced until it reaches a terminal state;
        # asyncio keeps only weak references to tasks. Each handler instance is
        # attached to a long-lived resource route.
        self._background_tasks: set[asyncio.Task[Any]] = set()

    @staticmethod
    def _state_value(request: StarletteRequest, name: str) -> Any | None:
        """Read an explicitly stored app-state value without MagicMock leaks."""
        app = getattr(request, "app", None)
        state = getattr(app, "state", None)
        if isinstance(state, Mapping):
            return state.get(name)
        storage = getattr(state, "_state", None)
        if isinstance(storage, Mapping):
            return storage.get(name)
        try:
            values = vars(state)
        except TypeError:
            return None
        return values.get(name) if isinstance(values, Mapping) else None

    @classmethod
    def _progress_components(
        cls, request: StarletteRequest
    ) -> tuple[Any, Any, str] | None:
        """Resolve the tracker, owner registry, and caller identity.

        The generic resource handler is also used in standalone/unit setups,
        so progress is opt-in through explicit mounted app state. Missing or
        incomplete infrastructure deliberately selects the synchronous path.
        """
        tracker = cls._state_value(request, "progress_tracker")
        access = cls._state_value(request, "progress_access")
        if tracker is None or access is None:
            return None
        required_tracker_methods = ("update", "complete", "fail", "get", "subscribe")
        if not all(
            callable(getattr(tracker, method, None))
            for method in required_tracker_methods
        ):
            return None
        if not callable(getattr(access, "register", None)) or not callable(
            getattr(access, "unregister", None)
        ):
            return None
        from lexigram.admin.controllers.progress import progress_principal_key

        owner_key = progress_principal_key(request)
        if not owner_key:
            return None
        return tracker, access, owner_key

    @staticmethod
    async def _publish_progress(
        tracker: Any | None,
        task_id: str,
        current: int,
        total: int,
        message: str,
    ) -> None:
        """Publish an update without allowing tracker outages to break writes."""
        if tracker is None:
            return
        try:
            await tracker.update(task_id, current, total, message)
        except Exception:  # noqa: BLE001 — progress is observational only
            logger.warning(
                "admin.bulk_progress_update_failed",
                task_id=task_id,
                current=current,
                total=total,
            )

    @staticmethod
    async def _terminal_progress(
        tracker: Any,
        method_name: str,
        task_id: str,
        value: str,
        metadata: dict[str, Any],
    ) -> None:
        """Call a terminal tracker method with old-implementation compatibility."""
        method = getattr(tracker, method_name)
        try:
            parameters = inspect.signature(method).parameters.values()
            accepts_metadata = any(
                parameter.name == "metadata"
                or parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in parameters
            )
        except (TypeError, ValueError):
            # Some extension callables do not expose a signature. Try the
            # current form; the outer task handler treats a failure as
            # observational and does not undo the mutation.
            accepts_metadata = True

        if accepts_metadata:
            result = method(task_id, value, metadata=metadata)
        else:
            result = method(task_id, value)
        if inspect.isawaitable(result):
            await result

    @classmethod
    async def _safe_terminal_progress(
        cls,
        tracker: Any,
        method_name: str,
        task_id: str,
        value: str,
        metadata: dict[str, Any],
    ) -> None:
        """Best-effort terminal publication for a background mutation."""
        try:
            await cls._terminal_progress(tracker, method_name, task_id, value, metadata)
        except Exception:  # noqa: BLE001 — tracker failures are non-fatal
            logger.warning(
                "admin.bulk_progress_terminal_failed",
                task_id=task_id,
                status="failed" if method_name == "fail" else "complete",
            )

    @classmethod
    async def _run_progress_bulk(
        cls,
        tracker: Any,
        task_id: str,
        resource: Any,
        data_source: Any,
        action: str,
        item_ids: list[str],
    ) -> None:
        """Run a built-in bulk mutation and publish its terminal outcome."""
        try:
            if action == "delete":
                outcome = await cls._bulk_delete(
                    resource,
                    data_source,
                    item_ids,
                    purge=False,
                    progress=tracker,
                    task_id=task_id,
                )
            elif action == "purge":
                outcome = await cls._bulk_delete(
                    resource,
                    data_source,
                    item_ids,
                    purge=True,
                    progress=tracker,
                    task_id=task_id,
                )
            else:
                outcome = await cls._bulk_restore(
                    resource,
                    data_source,
                    item_ids,
                    progress=tracker,
                    task_id=task_id,
                )

            logger.info(
                "admin.bulk_outcome",
                resource=str(resource.name or ""),
                action=action,
                task_id=task_id,
                **outcome.log_fields(),
            )
            message = outcome.message()
            await cls._safe_terminal_progress(
                tracker,
                "complete",
                task_id,
                message,
                {
                    "toast_type": outcome.toast_type(),
                    "duration": 8000 if not outcome.all_ok else 3000,
                    "refresh": True,
                },
            )
        except NotImplementedError:
            error = {
                "delete": "Delete is unavailable",
                "purge": "Purge is unavailable",
                "restore": "Restore is unavailable",
            }[action]
            await cls._safe_terminal_progress(
                tracker,
                "fail",
                task_id,
                error,
                {"toast_type": "error", "duration": 8000, "refresh": False},
            )
        except (PermissionError, PermissionDeniedError):
            await cls._safe_terminal_progress(
                tracker,
                "fail",
                task_id,
                "Forbidden",
                {"toast_type": "error", "duration": 8000, "refresh": False},
            )
        except Exception:  # noqa: BLE001 — details stay in server logs
            logger.exception(
                "admin.bulk_progress_operation_failed",
                task_id=task_id,
                action=action,
            )
            message = {
                "delete": "Unable to delete selected records",
                "purge": "Unable to purge selected records",
                "restore": "Unable to restore selected records",
            }[action]
            await cls._safe_terminal_progress(
                tracker,
                "fail",
                task_id,
                message,
                {"toast_type": "error", "duration": 8000, "refresh": False},
            )

    async def _queue_progress_bulk(
        self,
        request: StarletteRequest,
        resource: Any,
        data_source: Any,
        action: str,
        item_ids: list[str],
    ) -> Response | None:
        """Queue a large built-in mutation, or return ``None`` to run inline."""
        components = self._progress_components(request)
        if components is None or len(item_ids) < self.BULK_PROGRESS_THRESHOLD:
            return None
        tracker, access, owner_key = components
        task_id = f"bulk-{secrets.token_urlsafe(24)}"
        if not access.register(task_id, owner_key):
            return None

        try:
            # Publish before creating the task so the first browser SSE
            # connection cannot race an unknown task response.
            await tracker.update(
                task_id,
                0,
                len(item_ids),
                f"Queued {action} for {len(item_ids)} item(s)",
            )
            task = asyncio.create_task(
                self._run_progress_bulk(
                    tracker,
                    task_id,
                    resource,
                    data_source,
                    action,
                    list(item_ids),
                )
            )
        except Exception:  # noqa: BLE001 — valid mutation falls back inline
            access.unregister(task_id)
            logger.warning(
                "admin.bulk_progress_start_failed",
                task_id=task_id,
                action=action,
            )
            return None

        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        from urllib.parse import quote

        prefix = admin_prefix_from_request(request)
        encoded_id = quote(task_id, safe="")
        status_url = admin_url(prefix, "", f"progress/{encoded_id}")
        stream_url = admin_url(prefix, "", f"progress/{encoded_id}/stream")
        response = HTMLResponse("", status_code=202)
        response.headers["HX-Reswap"] = "none"
        response.headers["Cache-Control"] = "no-store"
        response.headers["HX-Trigger"] = dumps_str(
            {
                "bulk-progress-start": {
                    "task_id": task_id,
                    "status_url": status_url,
                    "stream_url": stream_url,
                    "total": len(item_ids),
                }
            }
        )
        logger.info(
            "admin.bulk_progress_started",
            task_id=task_id,
            resource=str(resource.name or ""),
            action=action,
            total=len(item_ids),
        )
        return response

    def can_handle(self, action: str) -> bool:
        return action in (
            "bulk",
            "bulk-delete-confirm",
            "bulk-purge-confirm",
            "bulk-restore-confirm",
        )

    @staticmethod
    async def _bulk_delete(
        resource: Any,
        data_source: Any,
        item_ids: list[str],
        *,
        purge: bool,
        progress: Any | None = None,
        task_id: str = "",
    ) -> BulkOutcome:
        """Delete selected records with per-row failure isolation (R14).

        Every id ends as a success or a failure with a reason; one bad row
        never aborts the rest of the batch. ``NotImplementedError`` still
        propagates — it means the operation is structurally unavailable and
        the caller maps it to a 503.
        """
        outcome = BulkOutcome(
            verb="Purged" if purge else "Deleted", total=len(item_ids)
        )
        processed = 0

        async def mark_processed() -> None:
            nonlocal processed
            processed += 1
            await BulkActionHandler._publish_progress(
                progress,
                task_id,
                processed,
                len(item_ids),
                f"{outcome.verb} {processed}/{len(item_ids)} item(s)",
            )

        if purge:
            operation = getattr(resource, "purge", None)
            if not callable(operation):
                # Mirrors the single-record purge path: without a purge hook
                # the operation is unavailable — never a silent no-op that
                # reports "Purged 0 item(s)" as success.
                raise NotImplementedError("purge is not supported")
            for item_id in item_ids:
                try:
                    await _maybe_await(operation(item_id))
                except LookupError:
                    outcome.record_failure(item_id, "not found")
                except NotImplementedError:
                    raise
                except (PermissionError, PermissionDeniedError):
                    outcome.record_failure(item_id, "forbidden")
                except Exception:  # noqa: BLE001 — row isolation; details stay private
                    logger.exception(
                        "admin.bulk_purge_row_failed", item_id=str(item_id)
                    )
                    outcome.record_failure(item_id, "error")
                else:
                    outcome.record_success()
                finally:
                    await mark_processed()
            return outcome

        for item_id in item_ids:
            try:
                item = await data_source.find_one(item_id)
                if item is None:
                    outcome.record_failure(item_id, "not found")
                    continue
                before_delete = getattr(resource, "before_delete", None)
                if callable(before_delete):
                    await _maybe_await(before_delete(item_id))
                if bool(getattr(resource, "soft_delete_enabled", False)):
                    from datetime import UTC, datetime

                    deleted = await data_source.update(
                        item_id, {"deleted_at": datetime.now(UTC).isoformat()}
                    )
                    success = deleted is not None
                else:
                    success = bool(await data_source.delete(item_id))
                if not success:
                    outcome.record_failure(item_id, "rejected by storage")
                    continue
                after_delete = getattr(resource, "after_delete", None)
                if callable(after_delete):
                    await _maybe_await(after_delete(item_id))
            except LookupError:
                outcome.record_failure(item_id, "not found")
            except NotImplementedError:
                raise
            except (PermissionError, PermissionDeniedError):
                outcome.record_failure(item_id, "forbidden")
            except Exception:  # noqa: BLE001 — row isolation; details stay private
                logger.exception("admin.bulk_delete_row_failed", item_id=str(item_id))
                outcome.record_failure(item_id, "error")
            else:
                outcome.record_success()
            finally:
                await mark_processed()
        return outcome

    @staticmethod
    async def _bulk_restore(
        resource: Any,
        data_source: Any,
        item_ids: list[str],
        *,
        progress: Any | None = None,
        task_id: str = "",
    ) -> BulkOutcome:
        """Restore selected records with per-row failure isolation (R14)."""
        operation = getattr(resource, "restore", None)
        outcome = BulkOutcome(verb="Restored", total=len(item_ids))
        processed = 0

        async def mark_processed() -> None:
            nonlocal processed
            processed += 1
            await BulkActionHandler._publish_progress(
                progress,
                task_id,
                processed,
                len(item_ids),
                f"{outcome.verb} {processed}/{len(item_ids)} item(s)",
            )

        for item_id in item_ids:
            try:
                if callable(operation):
                    restored = await _maybe_await(operation(item_id))
                    if restored is None:
                        outcome.record_failure(item_id, "restore rejected")
                        continue
                else:
                    updated = await data_source.update(item_id, {"deleted_at": None})
                    if updated is None:
                        outcome.record_failure(item_id, "not found")
                        continue
            except LookupError:
                outcome.record_failure(item_id, "not found")
            except NotImplementedError:
                raise
            except (PermissionError, PermissionDeniedError):
                outcome.record_failure(item_id, "forbidden")
            except Exception:  # noqa: BLE001 — row isolation; details stay private
                logger.exception("admin.bulk_restore_row_failed", item_id=str(item_id))
                outcome.record_failure(item_id, "error")
            else:
                outcome.record_success()
            finally:
                await mark_processed()
        return outcome

    @staticmethod
    def _declared_bulk_action(resource: Any, action_name: str) -> Any | None:
        """Find a server-backed bulk action declared by the resource.

        String declarations are UI-only compatibility shorthands; executable
        custom behavior must be represented by an action object (or a resource
        callback) so an arbitrary client-submitted action can never invoke an
        unregistered callable.
        """
        for declared in getattr(resource, "bulk_actions", None) or []:
            declared_name = (
                declared
                if isinstance(declared, str)
                else getattr(declared, "name", None)
            )
            if str(declared_name or "") == action_name:
                return declared
        return None

    @staticmethod
    async def _action_result_message(result: Any) -> tuple[bool, str]:
        """Normalize a Result-like action outcome to success/message."""
        if hasattr(result, "is_err") and result.is_err():
            error = result.unwrap_err()
            return False, str(getattr(error, "message", None) or error)
        if hasattr(result, "is_ok") and result.is_ok():
            result = result.unwrap()
        if isinstance(result, dict):
            return True, str(result.get("message") or "Bulk action completed")
        return True, str(result or "Bulk action completed")

    async def _execute_declared_action(
        self,
        request: StarletteRequest,
        resource: Any,
        data_source: Any,
        action_name: str,
        ids: list[str],
        form: Any,
    ) -> tuple[bool, str] | None:
        """Execute a declared custom bulk action, if it has a server hook."""
        declared = self._declared_bulk_action(resource, action_name)

        records = []
        for item_id in ids:
            item = await data_source.find_one(item_id)
            if item is not None:
                records.append(item)

        # A string declaration can opt into server behavior through the
        # explicit ``bulk_<action>`` resource callback. This keeps legacy
        # string configuration useful without treating an arbitrary request
        # value as a callable name.
        callback = None
        if isinstance(declared, str) or declared is None:
            callback = getattr(resource, f"bulk_{action_name}", None)

        if callable(callback):
            try:
                result = await _maybe_await(callback(records))
            except Exception:  # noqa: BLE001 — do not expose hook/storage details
                logger.exception("admin.resource_bulk_callback_failed")
                return False, "Bulk action failed"
            return await self._action_result_message(result)

        # The canonical admin action API owns authorization and execution.
        # Evaluate it against the complete selected-record set, and support
        # async overrides even though the base API is synchronous.
        executor = getattr(declared, "execute", None) if declared is not None else None
        if callable(executor):
            authorize = getattr(declared, "authorize", None)
            if callable(authorize):
                try:
                    allowed = await _maybe_await(
                        authorize(
                            records,
                            getattr(getattr(request, "state", None), "user", None),
                        )
                    )
                except Exception:  # noqa: BLE001 — authorization fails closed
                    logger.exception("admin.bulk_action_authorization_failed")
                    return False, "Forbidden"
                if hasattr(allowed, "is_err") and allowed.is_err():
                    error = allowed.unwrap_err()
                    return False, str(getattr(error, "message", None) or error)
                if allowed is False:
                    return False, "Forbidden"

            from lexigram.admin.actions.types import ActionContext

            context = ActionContext(
                request=request,
                user=getattr(getattr(request, "state", None), "user", None),
                resource_name=resource.name or "",
                resource_prefix=admin_url(
                    admin_prefix_from_request(request), resource.name or ""
                ),
                data_source=data_source,
                metadata={"form": form},
            )
            try:
                result = await _maybe_await(executor(records, context))
            except Exception:  # noqa: BLE001 — do not expose hook/storage details
                logger.exception("admin.bulk_action_execution_failed")
                return False, "Bulk action failed"
            return await self._action_result_message(result)

        if declared is None:
            return None

        # Deprecated ui.actions bulk declarations can still carry a callback.
        callback = getattr(declared, "_action", None)
        if callable(callback):
            try:
                result = await _maybe_await(callback(records))
            except Exception:  # noqa: BLE001 — do not expose hook/storage details
                logger.exception("admin.legacy_bulk_action_execution_failed")
                return False, "Bulk action failed"
            return await self._action_result_message(result)

        return False, f"Bulk action '{action_name}' is not executable"

    @staticmethod
    def _shape_export_record(item: Any) -> dict[str, Any]:
        """Normalize a record (mapping/model/object) to a plain dict."""
        if isinstance(item, dict):
            return dict(item)
        if hasattr(item, "model_dump"):
            return dict(item.model_dump())
        if hasattr(item, "dict") and callable(item.dict):
            return dict(item.dict())
        return dict(vars(item))

    async def _fetch_filtered_export_records(
        self, request: Any, resource: Any, list_query: str
    ) -> list[dict[str, Any]] | None:
        """Fetch every record matching the forwarded list state (R25).

        ``list_query`` is the list page's current querystring, parsed with
        the same ``TableState`` parser the list page uses so the export
        matches exactly what the user is looking at. The sort field is
        allowlisted against the resource's known fields (same posture as
        ``_sanitize_table_state`` on the list renderer). Results are paged
        through :class:`ListDataFetcher` — the same cache/search/resilience
        path as the list — and hard-capped at
        ``_MAX_FILTERED_EXPORT_ROWS``.

        Returns:
            Shaped records, or ``None`` when the fetch failed (callers
            should return an error response, not an empty file).
        """
        from types import SimpleNamespace

        from starlette.datastructures import QueryParams

        from lexigram.admin.resources.list_query import ListDataFetcher
        from lexigram.ui import TableState

        raw_query = str(list_query or "")
        if len(raw_query) > self._MAX_LIST_QUERY_LENGTH:
            return None
        try:
            params = QueryParams(raw_query.lstrip("?"))
            state = TableState.from_request(SimpleNamespace(query_params=params))
        except (ValueError, TypeError):
            return None

        columns_hook = getattr(resource, "columns", None)
        source_columns = list(columns_hook()) if callable(columns_hook) else []

        # Allowlist the URL-controlled sort field before it reaches storage.
        allowed_fields: set[str] = set()
        for column in source_columns:
            name = column if isinstance(column, str) else getattr(column, "name", None)
            if name:
                allowed_fields.add(str(name))
        sort_by = state.sort_by
        if sort_by:
            candidate = sort_by.lstrip("-")
            if allowed_fields and candidate not in allowed_fields:
                sort_by = None

        fetcher = ListDataFetcher(str(resource.name or ""))
        records: list[dict[str, Any]] = []
        page = 1
        while len(records) < self._MAX_FILTERED_EXPORT_ROWS:
            page_state = state.model_copy(
                update={
                    "page": page,
                    "per_page": self._FILTERED_EXPORT_PAGE_SIZE,
                    "cursor": None,
                    "sort_by": sort_by,
                }
            )
            try:
                items, _total = await fetcher.fetch_data(
                    request, resource, page_state, source_columns
                )
            except Exception:  # noqa: BLE001 — storage details stay private
                logger.exception("admin.filtered_export_fetch_failed")
                return None
            if fetcher.error and not items:
                return None
            batch = list(items or [])
            if not batch:
                break
            remaining = self._MAX_FILTERED_EXPORT_ROWS - len(records)
            records.extend(
                self._shape_export_record(item) for item in batch[:remaining]
            )
            if len(batch) < self._FILTERED_EXPORT_PAGE_SIZE:
                break
            page += 1
        return records

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        from lexigram.admin.resources.base import Resource as AdminResource
        from lexigram.admin.ui.organisms.admin_slide_over import (
            render_bulk_delete_confirm,
        )

        data_source = get_resource_data_source(resource)
        if not isinstance(resource, AdminResource) or data_source is None:
            return HTMLResponse(
                "<h1>Bulk actions not supported for this resource</h1>",
                status_code=400,
            )

        # ── Bulk confirmation (GET) ──
        if request.method == "GET":
            ids = request.query_params.getlist("ids")
            record_count = len(ids)
            bulk_url = admin_url(
                admin_prefix_from_request(request),
                resource.name or "",
                "bulk",
            )
            confirm_action = request.scope.get("admin_action", "bulk-delete-confirm")
            action, confirm_label, confirm_phrase = self._CONFIRM_LABELS.get(
                confirm_action, ("delete", "Delete", "DELETE")
            )
            html = render_bulk_delete_confirm(
                record_count=record_count,
                bulk_url=bulk_url,
                action=action,
                confirm_label=confirm_label,
                confirm_phrase=confirm_phrase,
            )
            return HTMLResponse(html)

        # ── Bulk action execution (POST) ──
        form = request.scope.get("admin_form_data")
        if form is None:
            try:
                form = await request.form()
            except (RuntimeError, ValueError, OSError, TypeError):
                return HTMLResponse("Invalid form submission", status_code=400)
        action_name = str(form.get("action", "") or "").strip()
        raw_ids = form.getlist("ids") if hasattr(form, "getlist") else []
        form_ids: list[str] = []
        seen_ids: set[str] = set()
        for raw_id in raw_ids:
            item_id = str(raw_id).strip()
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                form_ids.append(item_id)
        if len(form_ids) > self._MAX_SELECTED_IDS:
            return HTMLResponse(
                f"Select no more than {self._MAX_SELECTED_IDS} records",
                status_code=413,
            )
        # ``delete_selected`` is the legacy Resource string declaration. Keep
        # its public action name for rendering, but dispatch it through the
        # canonical delete implementation.
        execution_action = {"delete_selected": "delete"}.get(action_name, action_name)

        # Authorization for the generic endpoint is view-level so safe bulk
        # actions (such as export) remain available. Enforce the submitted
        # mutating action here as well, including legacy resource hooks.
        required_capability = {
            "delete": "can_delete",
            "purge": "can_delete",
            "restore": "can_update",
        }.get(execution_action)
        if required_capability:
            capabilities = getattr(getattr(request, "state", None), "permissions", None)
            if isinstance(capabilities, Mapping) and not capabilities.get(
                required_capability, False
            ):
                return HTMLResponse("Forbidden", status_code=403)
            hook_name = (
                "has_delete_permission"
                if required_capability == "can_delete"
                else "has_change_permission"
            )
            hook = getattr(resource, hook_name, None)
            if callable(hook):
                try:
                    allowed = await _maybe_await(
                        hook(getattr(getattr(request, "state", None), "user", None))
                    )
                except Exception:  # noqa: BLE001 — authorization fails closed
                    logger.exception("admin.bulk_resource_permission_failed")
                    return HTMLResponse("Forbidden", status_code=403)
                if not allowed:
                    return HTMLResponse("Forbidden", status_code=403)

        if not form_ids:
            # R25: an export submitted with scope=filtered and no ids means
            # "export everything matching the current list view".
            scope = str(form.get("scope", "") or "").strip().lower()
            filtered_export = (
                execution_action in {"export", "export_csv", "export_xlsx"}
                and scope == "filtered"
            )
            if not filtered_export:
                return HTMLResponse("No records selected", status_code=400)
        else:
            filtered_export = False

        is_htmx = request.headers.get("HX-Request") == "true"

        # Bulk UI visibility is not authorization. Mirror the single-record
        # delete guard for every selected record before performing any write,
        # so a protected row cannot be deleted through the bulk endpoint.
        if execution_action in {"delete", "purge"}:
            can_delete = getattr(resource, "can_delete", None)
            if can_delete:
                for item_id in form_ids:
                    try:
                        item = await data_source.find_one(item_id)
                    except Exception as exc:  # noqa: BLE001 — storage details stay private
                        logger.exception(
                            "admin.bulk_delete_lookup_failed", error=str(exc)
                        )
                        return HTMLResponse(
                            "Unable to load selected records", status_code=503
                        )
                    if item is None:
                        continue
                    try:
                        allowed = await _maybe_await(can_delete(item))
                    except Exception:  # noqa: BLE001 — record authorization fails closed
                        logger.exception("admin.bulk_delete_record_permission_failed")
                        allowed = False
                    if not allowed:
                        message = "One or more selected records cannot be deleted"
                        if is_htmx:
                            denied_response = HTMLResponse("", status_code=409)
                            denied_response.headers["HX-Trigger"] = (
                                '{"show-toast":{"message":"'
                                + message
                                + '","type":"error"}}'
                            )
                            return denied_response
                        return HTMLResponse(message, status_code=409)

        # Restore has the same record-level authorization boundary as delete.
        # Run it before queueing so the background task cannot outlive the
        # request's permission decision and mutate a newly-forbidden row.
        if execution_action == "restore":
            can_update = getattr(resource, "can_update", None)
            if can_update:
                for item_id in form_ids:
                    try:
                        item = await data_source.find_one(item_id)
                    except Exception as exc:  # noqa: BLE001 — storage details stay private
                        logger.exception(
                            "admin.bulk_restore_lookup_failed", error=str(exc)
                        )
                        return HTMLResponse(
                            "Unable to load selected records", status_code=503
                        )
                    if item is None:
                        continue
                    try:
                        allowed = await _maybe_await(can_update(item))
                    except Exception:  # noqa: BLE001 — record authorization fails closed
                        logger.exception("admin.bulk_restore_record_permission_failed")
                        allowed = False
                    if not allowed:
                        message = "One or more selected records cannot be restored"
                        if is_htmx:
                            denied_response = HTMLResponse("", status_code=409)
                            denied_response.headers["HX-Trigger"] = dumps_str(
                                {"show-toast": {"message": message, "type": "error"}}
                            )
                            return denied_response
                        return HTMLResponse(message, status_code=409)

        # Queue only the built-in mutating actions. Exports and custom declared
        # actions retain their existing request/response semantics.
        if is_htmx and execution_action in {"delete", "purge", "restore"}:
            progress_response = await self._queue_progress_bulk(
                request,
                resource,
                data_source,
                execution_action,
                form_ids,
            )
            if progress_response is not None:
                return progress_response

        # A declared action object owns custom execution. String declarations
        # without a server hook intentionally remain non-executable, except
        # for the legacy delete_selected alias handled below.
        if execution_action not in {
            "delete",
            "purge",
            "restore",
            "export",
            "export_csv",
            "export_xlsx",
        }:
            custom = await self._execute_declared_action(
                request,
                resource,
                data_source,
                action_name,
                form_ids,
                form,
            )
            if custom is None:
                return HTMLResponse(
                    render_to_string(el("p", f"Unknown action: {action_name}")),
                    status_code=400,
                )
            ok, message = custom
            if not ok:
                return HTMLResponse(
                    render_to_string(el("p", message)),
                    status_code=403 if message == "Forbidden" else 400,
                )
            if is_htmx:
                custom_response = HTMLResponse(render_to_string(el("p", message)))
                custom_response.headers["HX-Trigger"] = dumps_str(
                    {
                        "refresh-list": True,
                        "show-toast": {"message": message, "type": "success"},
                    }
                )
                return custom_response
            return RedirectResponse(
                url=admin_url(
                    admin_prefix_from_request(request),
                    resource.name or "",
                ),
                status_code=302,
            )

        if execution_action == "delete":
            try:
                outcome = await self._bulk_delete(
                    resource, data_source, form_ids, purge=False
                )
            except (PermissionError, PermissionDeniedError):
                return HTMLResponse("Forbidden", status_code=403)
            except NotImplementedError:
                return HTMLResponse("Delete is unavailable", status_code=503)
            except Exception as exc:  # noqa: BLE001 — storage/hook details stay private
                logger.exception("admin.bulk_delete_failed", error=str(exc))
                return HTMLResponse(
                    "Unable to delete selected records", status_code=503
                )
        elif execution_action == "purge":
            try:
                outcome = await self._bulk_delete(
                    resource, data_source, form_ids, purge=True
                )
            except (PermissionError, PermissionDeniedError):
                return HTMLResponse("Forbidden", status_code=403)
            except NotImplementedError:
                return HTMLResponse("Purge is unavailable", status_code=503)
            except Exception as exc:  # noqa: BLE001 — storage/hook details stay private
                logger.exception("admin.bulk_purge_failed", error=str(exc))
                return HTMLResponse("Unable to purge selected records", status_code=503)
        elif execution_action in {"export", "export_csv", "export_xlsx"}:
            import csv
            from io import StringIO

            if filtered_export:
                records = await self._fetch_filtered_export_records(
                    request, resource, str(form.get("list_query", "") or "")
                )
                if records is None:
                    return HTMLResponse(
                        "Unable to load records for export", status_code=503
                    )
            else:
                records = []
                for item_id in form_ids:
                    item = await data_source.find_one(item_id)
                    if item is None:
                        continue
                    records.append(self._shape_export_record(item))

            fieldnames: list[str] = []
            for record in records:
                for key in record:
                    if key not in fieldnames:
                        fieldnames.append(str(key))

            if execution_action == "export_xlsx":
                # R29: direct-download Excel. The shared encoder sanitizes
                # cells itself (formula guard + openpyxl type coercion).
                from lexigram.admin.services.export.xlsx import (
                    XLSX_CONTENT_TYPE,
                    encode_rows_as_xlsx,
                )

                try:
                    payload = encode_rows_as_xlsx(records, fieldnames or None)
                except ImportError as exc:
                    # Optional dependency absent — clear 501 beats a 500.
                    return HTMLResponse(str(exc), status_code=501)
                filename = f"{resource.name or 'records'}-export.xlsx"
                response: Response = Response(
                    content=payload, media_type=XLSX_CONTENT_TYPE
                )
            else:
                # Bulk CSV is an immediate download path and must retain the
                # same spreadsheet-formula protection as the background
                # export service.
                from lexigram.admin.services.export.sanitize import (
                    sanitize_cell_value,
                )

                records = [
                    {key: sanitize_cell_value(value) for key, value in record.items()}
                    for record in records
                ]
                output = StringIO()
                if fieldnames:
                    writer = csv.DictWriter(
                        output, fieldnames=fieldnames, extrasaction="ignore"
                    )
                    writer.writeheader()
                    writer.writerows(records)
                filename = f"{resource.name or 'records'}-export.csv"
                response = HTMLResponse(output.getvalue(), media_type="text/csv")
            response.headers["Content-Disposition"] = (
                f'attachment; filename="{filename}"'
            )
            # Exports may contain sensitive data — never cache (parity with
            # the controller-stack bulk_export path).
            response.headers["Cache-Control"] = "no-store"
            if is_htmx:
                # An HTMX swap must not put CSV bytes into the table. A
                # non-HTMX submission downloads normally; callers using HTMX
                # can consume the response as a download in their event hook.
                response.headers["HX-Reswap"] = "none"
            return response
        elif execution_action == "restore":
            try:
                outcome = await self._bulk_restore(resource, data_source, form_ids)
            except (PermissionError, PermissionDeniedError):
                return HTMLResponse("Forbidden", status_code=403)
            except NotImplementedError:
                return HTMLResponse("Restore is unavailable", status_code=503)
            except Exception as exc:  # noqa: BLE001 — storage/hook details stay private
                logger.exception("admin.bulk_restore_failed", error=str(exc))
                return HTMLResponse(
                    "Unable to restore selected records", status_code=503
                )
        else:
            return HTMLResponse(
                render_to_string(el("p", f"Unknown action: {action_name}")),
                status_code=400,
            )

        # Per-row outcome reporting (R14, doc 09): one structured log line
        # per batch with the full failure list, and an honest toast whose
        # severity reflects reality (success / warning / error).
        logger.info(
            "admin.bulk_outcome",
            resource=str(resource.name or ""),
            action=execution_action,
            **outcome.log_fields(),
        )
        message = outcome.message()

        if is_htmx:
            response = HTMLResponse(render_to_string(el("p", message)))
            toast: dict[str, Any] = {
                "message": message,
                "type": outcome.toast_type(),
            }
            if not outcome.all_ok:
                # Failure lists need more reading time than the 3s default.
                toast["duration"] = 8000
            response.headers["HX-Trigger"] = dumps_str(
                {
                    "refresh-list": True,
                    "show-toast": toast,
                }
            )
            return response
        return RedirectResponse(
            url=admin_url(
                admin_prefix_from_request(request),
                resource.name or "",
            ),
            status_code=302,
        )


class DefaultActionHandler:
    def can_handle(self, action: str) -> bool:
        return True

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        return HTMLResponse("<h1>Unknown action</h1>")


class ActionHandlerRegistry:
    """Registry for action handlers."""

    def __init__(self, config: AdminConfig, name: str, resources: dict | None = None):
        self._config = config
        self.name = name
        self._resources = resources or {}
        self._handlers: list[ResourceActionHandler] = []
        self._initialize_handlers()

    def _initialize_handlers(self) -> None:
        from lexigram.admin.engine.renderer import AdminRenderer as EngineAdminRenderer
        from lexigram.admin.resources.detail_renderer import DetailRenderer
        from lexigram.admin.resources.form_renderer import FormRenderer
        from lexigram.admin.resources.list_renderer import ListRenderer

        # AdminRenderer is stateless — nav is resolved from request.app.state at
        # render time, so a fresh instance per handler registry is safe.
        renderer = EngineAdminRenderer()

        list_renderer = ListRenderer(self._config, self.name, renderer)
        detail_renderer = DetailRenderer(self._config, self.name, renderer)
        form_renderer = FormRenderer(
            self._config,
            self.name,
            renderer,
            resources=self._resources,
        )

        self._handlers = [
            ListActionHandler(list_renderer),
            DetailActionHandler(detail_renderer),
            CreateActionHandler(form_renderer),
            EditActionHandler(form_renderer),
            CloneActionHandler(),
            RestoreActionHandler(),
            PurgeActionHandler(),
            DeleteActionHandler(),
            ImportActionHandler(),
            InlineMutationActionHandler(self._config, self.name),
            RelationOptionsActionHandler(self._resources),
            UserPermissionsActionHandler(self._config),
            BulkActionHandler(),
            DefaultActionHandler(),
        ]

    async def handle(
        self, request: StarletteRequest, resource: Any, action: str
    ) -> Any:
        for handler in self._handlers:
            if handler.can_handle(action):
                return await handler.handle(request, resource)
        return HTMLResponse("<h1>Unknown action</h1>")


@inject
class ResourceHandler:
    """Handler for resource routes."""

    def __init__(
        self,
        config: AdminConfig,
        name: str,
        action: str,
        resources: dict | None = None,
    ):
        self._config = config
        self.name = name
        self.action = action
        self._resources = resources or {}
        self._registry = ActionHandlerRegistry(config, name, resources=self._resources)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> Any:
        request = StarletteRequest(scope, receive, send)
        scope["admin_resource_prefix"] = self.name
        scope["admin_action"] = self.action
        scope["admin_prefix"] = self._config.prefix.rstrip("/")
        resource = self._resources.get(self.name) if self._resources else None
        if resource is not None:
            permission_method = {
                "list": "has_view_permission",
                "detail": "has_view_permission",
                "relation-options": "has_view_permission",
                "field": "has_change_permission",
                "inline": "has_change_permission",
                "inline-edit": "has_change_permission",
                "create": "has_add_permission",
                "import": "has_add_permission",
                "import-example": "has_add_permission",
                "import-report": "has_view_permission",
                "clone": "has_add_permission",
                "edit": "has_change_permission",
                "restore": "has_change_permission",
                "permissions": "has_change_permission",
                "delete": "has_delete_permission",
                "delete-confirm": "has_delete_permission",
                "purge": "has_delete_permission",
                # The generic endpoint also handles non-destructive bulk
                # actions (for example export); the handler checks the
                # submitted action's capability after parsing the form.
                "bulk": "has_view_permission",
                "bulk-delete-confirm": "has_delete_permission",
                "bulk-purge-confirm": "has_delete_permission",
                "bulk-restore-confirm": "has_change_permission",
            }.get(self.action)
            checker = (
                getattr(resource, permission_method, None)
                if permission_method
                else None
            )
            if callable(checker):
                user = getattr(request.state, "user", None)
                try:
                    allowed = checker(user)
                    if inspect.isawaitable(allowed):
                        allowed = await allowed
                except Exception:  # noqa: BLE001 — permission failures fail closed
                    logger.exception("admin.resource_permission_check_failed")
                    allowed = False
                if not allowed:
                    response = HTMLResponse("Forbidden", status_code=403)
                    await response(scope, receive, send)
                    return
        response = await self._registry.handle(request, resource, self.action)
        await response(scope, receive, send)
