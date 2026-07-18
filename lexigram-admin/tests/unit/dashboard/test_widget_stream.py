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
