"""Widget-stream SSE route: live push for dashboard widgets.

Wraps SubjectAdminEventHub in the sanctioned sse_from_stream bridge
(lexigram-web), narrowing the caller-requested `resources` filter to
only resources the caller is authorized to list via PermissionService.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.realtime import SubjectAdminEventHub
from lexigram.reactive import Stream
from lexigram.serialization import dumps_str
from lexigram.web.transport.reactive import sse_from_stream

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.responses import Response

    from lexigram.admin.rbac.service import PermissionService


async def authorized_resources(
    user: Any,
    requested: str | None,
    permission_service: PermissionService,
) -> list[str] | None:
    """Narrow a caller-supplied resources= filter to ones the caller may list.

    Fail-closed on resources with no registered permission schema:
    ``PermissionService.can_list`` itself returns ``True`` for unknown
    resources (management-UI semantics: no permission model = public),
    which is the wrong default on a channel boundary — a name without a
    schema is treated as unauthorized here.

    Args:
        user: The authenticated request user (or None).
        requested: Raw comma-separated `resources` query param value.
        permission_service: Resolves per-resource `can_list` authorization.

    Returns:
        The allowed subset, or None when nothing was requested or every
        requested resource was denied — both mean "apply no resource
        filter," and None is unambiguous where an empty list could be
        misread as "match nothing."
    """
    if not requested:
        return None
    candidates = [r.strip() for r in requested.split(",") if r.strip()]
    allowed = [
        r
        for r in candidates
        if permission_service.get_schema(r) is not None
        and await permission_service.can_list(user, r)
    ]
    return allowed or None


def build_widget_event_stream_handler(
    widget_hub: SubjectAdminEventHub,
    permission_service: PermissionService,
) -> Callable[[Request], Awaitable[Response]]:
    """Build the ASGI route handler for GET /admin/_sse/widgets.

    Args:
        widget_hub: Hub to subscribe to for live admin events.
        permission_service: Used to authorize the caller's resources= filter.

    Returns:
        An async Starlette-style route handler.
    """

    async def widget_event_stream(request: Request) -> Response:
        user = getattr(request.state, "user", None)
        user_id = getattr(user, "user_id", None) if user else None
        tenant_id = getattr(request.state, "tenant_id", None) or None
        resources = await authorized_resources(
            user, request.query_params.get("resources"), permission_service
        )

        def serialize(event: Any) -> str:
            return dumps_str(event.to_dict())

        return sse_from_stream(
            Stream(
                widget_hub.subscribe(
                    user_id=user_id,
                    resources=resources,
                    tenant_id=tenant_id,
                )
            ),
            serializer=serialize,
        )

    return widget_event_stream


__all__ = ["authorized_resources", "build_widget_event_stream_handler"]
