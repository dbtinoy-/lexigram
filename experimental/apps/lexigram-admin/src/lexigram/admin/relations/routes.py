"""Route registration for relation managers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from starlette.responses import HTMLResponse
from starlette.routing import Route

from lexigram.logging import get_logger
from lexigram.ui import el, render_to_string

if TYPE_CHECKING:
    from starlette.requests import Request

    from lexigram.admin.auth.protocols import AdminAuditLogServiceProtocol
    from lexigram.admin.exceptions import PermissionDeniedError
    from lexigram.admin.relations.manager_ext import RelationManager
    from lexigram.result import Result

logger = get_logger(__name__)


def register_relation_routes(
    resource_name: str,
    manager_class: type[RelationManager],
    *,
    parent_data_source: Any = None,
    audit_service: AdminAuditLogServiceProtocol | None = None,
) -> list[Route]:
    """Create Starlette Route objects for a relation manager.

    Args:
        resource_name: Registered resource name, used as the route prefix.
        manager_class: Relation manager class to mount.
        parent_data_source: Optional data source used to resolve the parent
            record before rendering (parent-IDOR gate). When ``None`` no
            parent gate is applied.
        audit_service: Optional audit service for best-effort
            permission-denied logging.

    Returns:
        The list of Starlette routes for the relation manager.
    """
    prefix = f"/{resource_name}"
    # B25: embed the manager's concrete relationship name in the paths.
    # A `{rel_name}` wildcard made every relation manager mount at the
    # SAME path — the first one served requests for every relation and
    # the rest were unreachable.
    rel = manager_class.get_relationship_name()

    async def _handle_list(request: Request) -> HTMLResponse:
        parent_id = request.path_params.get("parent_id", "")
        denied = await _require_user(request, audit_service)
        if denied:
            return denied
        mgr = _create_manager(manager_class, parent_id)
        parent, denied = await _require_parent(mgr, parent_data_source)
        if denied:
            return denied
        if parent is not None:
            check = await _check(mgr.can_view_parent, request, audit_service, parent)
            if check:
                return check
        html = await mgr.render(request, resource_name)
        return HTMLResponse(html)

    async def _handle_create_form(request: Request) -> HTMLResponse:
        parent_id = request.path_params.get("parent_id", "")
        denied = await _require_user(request, audit_service)
        if denied:
            return denied
        mgr = _create_manager(manager_class, parent_id)
        parent, denied = await _require_parent(mgr, parent_data_source)
        if denied:
            return denied
        if parent is not None:
            check = await _check(mgr.can_view_parent, request, audit_service, parent)
            if check:
                return check
        form = mgr.create_form()
        return HTMLResponse(form or "<div>No create form available</div>")

    async def _handle_create(request: Request) -> HTMLResponse:
        parent_id = request.path_params.get("parent_id", "")
        denied = await _require_user(request, audit_service)
        if denied:
            return denied
        mgr = _create_manager(manager_class, parent_id)
        _, denied = await _require_parent(mgr, parent_data_source)
        if denied:
            return denied
        check = await _check(mgr.can_create, request, audit_service)
        if check:
            return check
        await mgr.get_query()
        html = await mgr.render(request, resource_name)
        return HTMLResponse(html)

    async def _handle_edit_form(request: Request) -> HTMLResponse:
        parent_id = request.path_params.get("parent_id", "")
        record_id = request.path_params.get("record_id", "")
        denied = await _require_user(request, audit_service)
        if denied:
            return denied
        mgr = _create_manager(manager_class, parent_id)
        parent, denied = await _require_parent(mgr, parent_data_source)
        if denied:
            return denied
        if parent is not None:
            check = await _check(mgr.can_view_parent, request, audit_service, parent)
            if check:
                return check
        record = await _get_record(mgr, record_id)
        if record is not None:
            check = await _check(mgr.can_edit, request, audit_service, record)
            if check:
                return check
        form = mgr.edit_form(record) if record else None
        return HTMLResponse(
            form or render_to_string(el("div", "Edit form for ", record_id))
        )

    async def _handle_update(request: Request) -> HTMLResponse:
        parent_id = request.path_params.get("parent_id", "")
        record_id = request.path_params.get("record_id", "")
        denied = await _require_user(request, audit_service)
        if denied:
            return denied
        mgr = _create_manager(manager_class, parent_id)
        _, denied = await _require_parent(mgr, parent_data_source)
        if denied:
            return denied
        record = await _get_record(mgr, record_id)
        if record is None:
            return HTMLResponse("Not found", status_code=404)
        check = await _check(mgr.can_edit, request, audit_service, record)
        if check:
            return check
        html = await mgr.render(request, resource_name)
        return HTMLResponse(html)

    async def _handle_delete(request: Request) -> HTMLResponse:
        parent_id = request.path_params.get("parent_id", "")
        record_id = request.path_params.get("record_id", "")
        denied = await _require_user(request, audit_service)
        if denied:
            return denied
        mgr = _create_manager(manager_class, parent_id)
        _, denied = await _require_parent(mgr, parent_data_source)
        if denied:
            return denied
        record = await _get_record(mgr, record_id)
        if record is None:
            return HTMLResponse("Not found", status_code=404)
        check = await _check(mgr.can_delete, request, audit_service, record)
        if check:
            return check
        return HTMLResponse("")

    async def _run_pivot_handler(
        request: Request,
        handler_name: str,
    ) -> HTMLResponse:
        """Shared gate + dispatch for the pivot POST handlers (B27)."""
        from lexigram.admin.relations.errors import RelationPersistenceError

        parent_id = request.path_params.get("parent_id", "")
        denied = await _require_user(request, audit_service)
        if denied:
            return denied
        mgr = _create_manager(manager_class, parent_id)
        parent, denied = await _require_parent(mgr, parent_data_source)
        if denied:
            return denied
        if parent is not None:
            check = await _check(mgr.can_view_parent, request, audit_service, parent)
            if check:
                return check
        try:
            return await getattr(mgr, handler_name)(request, resource_name)
        except RelationPersistenceError as exc:
            return HTMLResponse(str(exc), status_code=400)

    async def _handle_toggle(request: Request) -> HTMLResponse:
        return await _run_pivot_handler(request, "handle_toggle")

    async def _handle_sync(request: Request) -> HTMLResponse:
        return await _run_pivot_handler(request, "handle_sync")

    async def _handle_pivot_update(request: Request) -> HTMLResponse:
        return await _run_pivot_handler(request, "handle_pivot_update")

    routes = [
        Route(
            path=f"{prefix}/{{parent_id}}/relations/{rel}",
            endpoint=_handle_list,
            methods=["GET"],
        ),
        Route(
            path=f"{prefix}/{{parent_id}}/relations/{rel}/new",
            endpoint=_handle_create_form,
            methods=["GET"],
        ),
        Route(
            path=f"{prefix}/{{parent_id}}/relations/{rel}",
            endpoint=_handle_create,
            methods=["POST"],
        ),
        Route(
            path=f"{prefix}/{{parent_id}}/relations/{rel}/{{record_id}}/edit",
            endpoint=_handle_edit_form,
            methods=["GET"],
        ),
        Route(
            path=f"{prefix}/{{parent_id}}/relations/{rel}/{{record_id}}",
            endpoint=_handle_update,
            methods=["PUT"],
        ),
        Route(
            path=f"{prefix}/{{parent_id}}/relations/{rel}/{{record_id}}",
            endpoint=_handle_delete,
            methods=["DELETE"],
        ),
    ]

    # B27: mount the pivot surface (attach/detach toggle, bulk sync,
    # inline pivot edits) for managers that provide it. These handlers
    # previously existed only inside get_pivot_routes(), which nothing
    # mounted — the rendered checkboxes/Save button/pivot inputs all
    # posted into 404s.
    if all(
        hasattr(manager_class, name)
        for name in ("handle_toggle", "handle_sync", "handle_pivot_update")
    ):
        routes.extend(
            [
                Route(
                    path=f"{prefix}/{{parent_id}}/relations/{rel}/toggle",
                    endpoint=_handle_toggle,
                    methods=["POST"],
                ),
                Route(
                    path=f"{prefix}/{{parent_id}}/relations/{rel}/sync",
                    endpoint=_handle_sync,
                    methods=["POST"],
                ),
                Route(
                    path=f"{prefix}/{{parent_id}}/relations/{rel}/pivot/{{related_id}}",
                    endpoint=_handle_pivot_update,
                    methods=["POST"],
                ),
            ]
        )

    return routes


def _create_manager(
    manager_class: type[RelationManager], parent_id: Any
) -> RelationManager:
    return manager_class(parent_id=parent_id)


async def _get_record(mgr: RelationManager, record_id: str) -> Any:
    items = await mgr.get_query()
    for item in items:
        # B26: dict-aware — SQL data sources return dict rows.
        rid = mgr._row_id(item)
        if rid is not None and str(rid) == record_id:
            return item
    return None


async def _require_parent(
    mgr: RelationManager,
    parent_data_source: Any,
) -> tuple[Any | None, HTMLResponse | None]:
    """Resolve the parent record through the data source, or a 404.

    Args:
        mgr: The relation manager whose ``parent_id`` is being resolved.
        parent_data_source: The resource data source, or ``None`` to skip
            the parent gate entirely.

    Returns:
        ``(parent, None)`` on success with the resolved parent also
        attached to ``mgr.parent``; ``(None, None)`` when no data source
        is mounted; ``(None, 404 response)`` when the parent record does
        not exist.
    """
    if parent_data_source is None:
        return None, None
    parent = await parent_data_source.find_one(mgr.parent_id)
    if parent is None:
        return None, HTMLResponse("Parent not found", status_code=404)
    mgr.parent = parent
    return parent, None


async def _check(
    predicate: Callable[..., Result[None, PermissionDeniedError]],
    request: Request,
    audit_service: AdminAuditLogServiceProtocol | None,
    *args: Any,
) -> HTMLResponse | None:
    """Run a permission predicate, denying with a 403 response on failure.

    Args:
        predicate: Manager predicate returning ``Result[None,
            PermissionDeniedError]``.
        request: The request whose ``state`` carries the resolved user.
        audit_service: Optional audit service for best-effort denial logging.
        *args: Extra predicate arguments (parent entity, record, ...).

    Returns:
        A 403 HTMLResponse when the predicate denies or no user is
        present (fail-closed), ``None`` to let the handler proceed.
    """
    action = f"relation.{predicate.__name__}"
    parent_id = request.path_params.get("parent_id", "")
    user = getattr(getattr(request, "state", None), "user", None)
    if user is None:
        return await _deny(request, audit_service, action, parent_id=parent_id)
    result = predicate(*args, user)
    if result.is_err():
        return await _deny(request, audit_service, action, parent_id=parent_id)
    return None


async def _require_user(
    request: Request,
    audit_service: AdminAuditLogServiceProtocol | None,
) -> HTMLResponse | None:
    """Deny unauthenticated route traffic with a 403, fail-closed.

    The authorization middleware normally redirects unauthenticated
    requests before routing; this gate keeps handlers fail-closed when
    invoked directly.

    Args:
        request: The request whose ``state`` carries the resolved user.
        audit_service: Optional audit service for best-effort denial logging.

    Returns:
        A 403 HTMLResponse when no user is present, ``None`` otherwise.
    """
    user = getattr(getattr(request, "state", None), "user", None)
    if user is None:
        return await _deny(request, audit_service, "relation.access")
    return None


async def _deny(
    request: Request,
    audit_service: AdminAuditLogServiceProtocol | None,
    action: str,
    parent_id: Any = "",
) -> HTMLResponse:
    """Return a 403 denial response, recording the event best-effort."""
    await _audit_denial(request, audit_service, action=action, parent_id=parent_id)
    return HTMLResponse("Permission denied", status_code=403)


async def _audit_denial(
    request: Request,
    audit_service: AdminAuditLogServiceProtocol | None,
    *,
    action: str,
    parent_id: Any = "",
) -> None:
    """Append a permission denial to the security audit log, best-effort."""
    if not audit_service:
        return
    from lexigram.admin.auth.types import AdminSecurityEventType

    try:
        client = getattr(request, "client", None)
        await audit_service.log_event(
            event_type=AdminSecurityEventType.PERMISSION_DENIED,
            ip_address=getattr(client, "host", "unknown"),
            user_agent=request.headers.get("user-agent", "") or "",
            success=False,
            metadata={"action": action, "parent_id": str(parent_id)},
        )
    except Exception:  # noqa: BLE001 — audit failures must not break denials
        logger.warning("relations.audit_failed", action=action)


__all__ = [
    "register_relation_routes",
]
