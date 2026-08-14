"""Unit tests for the widget-stream SSE route's resource-authorization narrowing.

The surrounding transport (SSE framing, keepalive, request-entry auth
middleware) is already covered by lexigram-web's sse_from_stream tests
and lexigram-admin's AdminAuthorizationMiddleware tests respectively —
not duplicated here. This file covers only the logic specific to this
route: narrowing a caller-supplied resources= filter to resources the
caller is actually authorized to list.
"""

from __future__ import annotations

from types import SimpleNamespace

from lexigram.admin.dashboard.widget_stream import authorized_resources


class _FakePermissionService:
    def __init__(self, allowed: set[str]) -> None:
        self._allowed = allowed
        self._schemas: dict[str, object] = {name: object() for name in allowed}

    def get_schema(self, resource_name: str) -> object | None:
        return self._schemas.get(resource_name)

    async def can_list(self, user: object, resource_name: str) -> bool:
        return resource_name in self._allowed


async def test_authorized_resources_none_when_nothing_requested() -> None:
    result = await authorized_resources(
        SimpleNamespace(user_id="u1"), None, _FakePermissionService({"users"})
    )
    assert result is None


async def test_authorized_resources_drops_unauthorized() -> None:
    result = await authorized_resources(
        SimpleNamespace(user_id="u1"),
        "users,secret_resource",
        _FakePermissionService({"users"}),
    )
    assert result == ["users"]


async def test_authorized_resources_all_denied_returns_none() -> None:
    """All-denied returns None (no filter applied at the hub), not [].

    Distinguishing "nothing requested" from "everything denied" doesn't
    matter to the hub (both mean "don't filter by resource"), but an
    empty list is easy to misread at a call site as "match nothing" —
    None is unambiguous.
    """
    result = await authorized_resources(
        SimpleNamespace(user_id="u1"),
        "secret_resource",
        _FakePermissionService(set()),
    )
    assert result is None


async def test_authorized_resources_fail_closed_on_schema_less_resource() -> None:
    """Unknown resources are fail-closed on this channel boundary.

    PermissionService.can_list itself returns True when a resource has
    no registered schema (UI semantics: no permission model = public).
    On an SSE channel that would leak broadcasts to any requested name,
    so authorized_resources requires a schema before consulting
    can_list — an unknown name is treated as unauthorized.
    """
    result = await authorized_resources(
        SimpleNamespace(user_id="u1"),
        "unmodeled_resource",
        _FakePermissionService({"users"}),
    )
    assert result is None

    result = await authorized_resources(
        SimpleNamespace(user_id="u1"),
        "users,unmodeled_resource",
        _FakePermissionService({"users"}),
    )
    assert result == ["users"]


async def test_authorized_resources_strips_whitespace() -> None:
    result = await authorized_resources(
        SimpleNamespace(user_id="u1"),
        " users,  secret_resource ",
        _FakePermissionService({"users"}),
    )
    assert result == ["users"]
