"""Route registration for relation managers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.responses import HTMLResponse
from starlette.routing import Route

if TYPE_CHECKING:
    from starlette.requests import Request

    from lexigram.admin.relations.manager_ext import RelationManager


def register_relation_routes(
    resource_name: str,
    manager_class: type[RelationManager],
) -> list[Route]:
    """Create Starlette Route objects for a relation manager."""
    prefix = f"/{resource_name}"

    async def _handle_list(request: Request) -> HTMLResponse:
        parent_id = request.path_params.get("parent_id", "")
        mgr = _create_manager(manager_class, parent_id)
        html = await mgr.render(request, resource_name)
        return HTMLResponse(html)

    async def _handle_create_form(request: Request) -> HTMLResponse:
        parent_id = request.path_params.get("parent_id", "")
        mgr = _create_manager(manager_class, parent_id)
        form = mgr.create_form()
        return HTMLResponse(form or "<div>No create form available</div>")

    async def _handle_create(request: Request) -> HTMLResponse:
        parent_id = request.path_params.get("parent_id", "")
        mgr = _create_manager(manager_class, parent_id)
        await mgr.get_query()
        html = await mgr.render(request, resource_name)
        return HTMLResponse(html)

    async def _handle_edit_form(request: Request) -> HTMLResponse:
        parent_id = request.path_params.get("parent_id", "")
        record_id = request.path_params.get("record_id", "")
        mgr = _create_manager(manager_class, parent_id)
        record = await _get_record(mgr, record_id)
        form = mgr.edit_form(record) if record else None
        return HTMLResponse(form or f"<div>Edit form for {record_id}</div>")

    async def _handle_update(request: Request) -> HTMLResponse:
        parent_id = request.path_params.get("parent_id", "")
        record_id = request.path_params.get("record_id", "")
        mgr = _create_manager(manager_class, parent_id)
        html = await mgr.render(request, resource_name)
        return HTMLResponse(html)

    async def _handle_delete(request: Request) -> HTMLResponse:
        parent_id = request.path_params.get("parent_id", "")
        record_id = request.path_params.get("record_id", "")
        mgr = _create_manager(manager_class, parent_id)
        return HTMLResponse("")

    return [
        Route(
            path=f"{prefix}/{{parent_id}}/relations/{{rel_name}}",
            endpoint=_handle_list,
            methods=["GET"],
        ),
        Route(
            path=f"{prefix}/{{parent_id}}/relations/{{rel_name}}/new",
            endpoint=_handle_create_form,
            methods=["GET"],
        ),
        Route(
            path=f"{prefix}/{{parent_id}}/relations/{{rel_name}}",
            endpoint=_handle_create,
            methods=["POST"],
        ),
        Route(
            path=f"{prefix}/{{parent_id}}/relations/{{rel_name}}/{{record_id}}/edit",
            endpoint=_handle_edit_form,
            methods=["GET"],
        ),
        Route(
            path=f"{prefix}/{{parent_id}}/relations/{{rel_name}}/{{record_id}}",
            endpoint=_handle_update,
            methods=["PUT"],
        ),
        Route(
            path=f"{prefix}/{{parent_id}}/relations/{{rel_name}}/{{record_id}}",
            endpoint=_handle_delete,
            methods=["DELETE"],
        ),
    ]


def _create_manager(
    manager_class: type[RelationManager], parent_id: Any
) -> RelationManager:
    return manager_class(parent_id=parent_id)


async def _get_record(mgr: RelationManager, record_id: str) -> Any:
    items = await mgr.get_query()
    for item in items:
        if str(getattr(item, "id", "")) == record_id:
            return item
    return None


__all__ = [
    "register_relation_routes",
]
