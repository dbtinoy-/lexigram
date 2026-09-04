"""ListRenderer saved-views bar tests (R13 — docs/09-01-2026/08-saved-views.md)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.resources.list_renderer import ListRenderer
from lexigram.admin.services.saved_views import SavedViewService
from lexigram.ui import TableState


class _FakeSettings:
    def __init__(self) -> None:
        self.data: dict[tuple[str, str], Any] = {}

    async def get(self, tenant_id: str, name: str) -> Any:
        return self.data.get((tenant_id, name))

    async def set(self, tenant_id: str, name: str, value: Any) -> None:
        self.data[(tenant_id, name)] = value


def _renderer(resource_name: str = "users") -> ListRenderer:
    return ListRenderer(MagicMock(), resource_name, MagicMock())


def _request(
    service: SavedViewService | None,
    user: Any = None,
    csrf_value: str = "tok-123",
    *,
    raw_query: str = "",
    query_params: Any | None = None,
    headers: dict[str, str] | None = None,
) -> SimpleNamespace:
    app_state = SimpleNamespace()
    if service is not None:
        app_state.saved_view_service = service
    return SimpleNamespace(
        app=SimpleNamespace(state=app_state),
        state=SimpleNamespace(user=user, csrf_token=csrf_value),
        headers=headers or {},
        query_params={} if query_params is None else query_params,
        url=SimpleNamespace(query=raw_query),
    )


def _user(user_id: str = "u-1") -> SimpleNamespace:
    return SimpleNamespace(user_id=user_id)


_STATE = TableState()
_FILTERED_STATE = TableState(filters={"status": "active"}, sort_by="name")


class TestBarVisibility:
    @pytest.mark.asyncio
    async def test_no_service_renders_nothing(self) -> None:
        html = await _renderer()._render_saved_views_bar(
            _request(None, user=_user()), _STATE, "/admin/users", "/admin"
        )
        assert html == ""

    @pytest.mark.asyncio
    async def test_guest_user_renders_nothing(self) -> None:
        service = SavedViewService(_FakeSettings())
        html = await _renderer()._render_saved_views_bar(
            _request(service, user=_user("guest")), _STATE, "/admin/users", "/admin"
        )
        assert html == ""

    @pytest.mark.asyncio
    async def test_missing_user_renders_nothing(self) -> None:
        service = SavedViewService(_FakeSettings())
        html = await _renderer()._render_saved_views_bar(
            _request(service, user=None), _STATE, "/admin/users", "/admin"
        )
        assert html == ""

    @pytest.mark.asyncio
    async def test_bar_rendered_with_no_views_shows_save_form(self) -> None:
        service = SavedViewService(_FakeSettings())
        html = await _renderer()._render_saved_views_bar(
            _request(service, user=_user()), _STATE, "/admin/users", "/admin"
        )
        assert "data-saved-views" in html
        assert "data-saved-view-save" in html
        assert 'action="/admin/views/users/save"' in html
        assert 'name="csrf_token" value="tok-123"' in html


class TestBarContent:
    @pytest.mark.asyncio
    async def test_saved_views_listed_as_links_with_delete_forms(self) -> None:
        service = SavedViewService(_FakeSettings())
        await service.save_view("u-1", "users", "Active", "filter_status=active")
        html = await _renderer()._render_saved_views_bar(
            _request(service, user=_user()), _STATE, "/admin/users", "/admin"
        )
        assert 'href="/admin/users?filter_status=active"' in html
        assert ">Active</a>" in html
        assert 'action="/admin/views/users/delete"' in html

    @pytest.mark.asyncio
    async def test_view_names_are_escaped(self) -> None:
        service = SavedViewService(_FakeSettings())
        await service.save_view("u-1", "users", "<script>alert(1)</script>", "search=a")
        html = await _renderer()._render_saved_views_bar(
            _request(service, user=_user()), _STATE, "/admin/users", "/admin"
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    @pytest.mark.asyncio
    async def test_active_view_highlighted(self) -> None:
        service = SavedViewService(_FakeSettings())
        await service.save_view(
            "u-1", "users", "Sorted", "sort_by=name&filter_status=active"
        )
        html = await _renderer()._render_saved_views_bar(
            _request(service, user=_user()),
            _FILTERED_STATE,
            "/admin/users",
            "/admin",
        )
        assert "border-primary" in html

    @pytest.mark.asyncio
    async def test_inactive_view_not_highlighted(self) -> None:
        service = SavedViewService(_FakeSettings())
        await service.save_view("u-1", "users", "Other", "search=zzz")
        html = await _renderer()._render_saved_views_bar(
            _request(service, user=_user()), _STATE, "/admin/users", "/admin"
        )
        assert "border-primary" not in html

    @pytest.mark.asyncio
    async def test_active_match_ignores_default_valued_params(self) -> None:
        # A saved query that spells out a resource default (per_page=10 when
        # the default is 10) must still match the current state, whose clean
        # URL omits defaults.
        service = SavedViewService(_FakeSettings())
        await service.save_view(
            "u-1", "users", "Mine", "search=chair&sort_order=desc&per_page=10"
        )
        state = TableState(search="chair", sort_order="desc", per_page=10)
        object.__setattr__(state, "_defaults", {"per_page": 10})
        html = await _renderer()._render_saved_views_bar(
            _request(service, user=_user()), state, "/admin/users", "/admin"
        )
        assert "border-primary" in html

    @pytest.mark.asyncio
    async def test_save_form_carries_current_sanitized_query(self) -> None:
        service = SavedViewService(_FakeSettings())
        html = await _renderer()._render_saved_views_bar(
            _request(service, user=_user()),
            _FILTERED_STATE,
            "/admin/users",
            "/admin",
        )
        assert 'name="query" value="' in html
        assert "filter_status=active" in html
        assert "sort_by=name" in html
        assert "page=" not in html

    @pytest.mark.asyncio
    async def test_default_view_has_clear_control(self) -> None:
        service = SavedViewService(_FakeSettings())
        await service.save_view("u-1", "users", "Mine", "search=a")
        await service.set_default_view("u-1", "users", "Mine")
        html = await _renderer()._render_saved_views_bar(
            _request(service, user=_user()), _STATE, "/admin/users", "/admin"
        )
        assert 'action="/admin/views/users/default"' in html
        assert 'name="default" value="0"' in html
        assert "Clear default view Mine" in html
        assert "★" in html

    @pytest.mark.asyncio
    async def test_non_default_view_has_set_control(self) -> None:
        service = SavedViewService(_FakeSettings())
        await service.save_view("u-1", "users", "Mine", "search=a")
        html = await _renderer()._render_saved_views_bar(
            _request(service, user=_user()), _STATE, "/admin/users", "/admin"
        )
        assert 'name="default" value="1"' in html
        assert "Set Mine as default view" in html
        assert "☆" in html


class TestDefaultRedirect:
    @pytest.mark.asyncio
    async def test_clean_full_page_visit_redirects_to_default(self) -> None:
        service = SavedViewService(_FakeSettings())
        await service.save_view("u-1", "users", "Mine", "search=active&page=4")
        await service.set_default_view("u-1", "users", "Mine")
        response = await _renderer()._default_view_redirect(
            _request(service, user=_user()), "/admin/users"
        )
        assert response is not None
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/users?search=active"

    @pytest.mark.asyncio
    async def test_render_returns_default_redirect_before_fetching(self) -> None:
        service = SavedViewService(_FakeSettings())
        await service.save_view("u-1", "users", "Mine", "search=active")
        await service.set_default_view("u-1", "users", "Mine")
        response = await _renderer().render(
            _request(service, user=_user()), MagicMock(), user=_user()
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/users?search=active"

    @pytest.mark.asyncio
    async def test_explicit_query_is_authoritative(self) -> None:
        service = SavedViewService(_FakeSettings())
        await service.save_view("u-1", "users", "Mine", "search=active")
        await service.set_default_view("u-1", "users", "Mine")
        request = _request(
            service,
            user=_user(),
            raw_query="search=other",
            query_params={"search": "other"},
        )
        assert await _renderer()._default_view_redirect(request, "/admin/users") is None

    @pytest.mark.asyncio
    async def test_explicit_pagination_is_authoritative(self) -> None:
        service = SavedViewService(_FakeSettings())
        await service.save_view("u-1", "users", "Mine", "search=active")
        await service.set_default_view("u-1", "users", "Mine")
        request = _request(
            service, user=_user(), raw_query="page=2", query_params={"page": "2"}
        )
        assert await _renderer()._default_view_redirect(request, "/admin/users") is None

    @pytest.mark.asyncio
    async def test_mutation_notice_is_preserved(self) -> None:
        service = SavedViewService(_FakeSettings())
        await service.save_view("u-1", "users", "Mine", "search=active")
        await service.set_default_view("u-1", "users", "Mine")
        request = _request(
            service,
            user=_user(),
            raw_query="notice=Default+view+cleared.",
            query_params={"notice": "Default view cleared."},
        )
        assert await _renderer()._default_view_redirect(request, "/admin/users") is None

    @pytest.mark.asyncio
    async def test_htmx_fragment_is_never_redirected(self) -> None:
        service = SavedViewService(_FakeSettings())
        await service.save_view("u-1", "users", "Mine", "search=active")
        await service.set_default_view("u-1", "users", "Mine")
        request = _request(
            service,
            user=_user(),
            headers={"HX-Target": "table-data"},
        )
        assert await _renderer()._default_view_redirect(request, "/admin/users") is None

    @pytest.mark.asyncio
    async def test_default_storage_failure_falls_through(self) -> None:
        service = MagicMock(spec=SavedViewService)
        service.get_default_view = AsyncMock(side_effect=RuntimeError("boom"))
        request = _request(service, user=_user())
        assert await _renderer()._default_view_redirect(request, "/admin/users") is None


class TestRobustness:
    @pytest.mark.asyncio
    async def test_broken_service_degrades_to_empty(self) -> None:
        service = MagicMock(spec=SavedViewService)
        service.list_views.side_effect = RuntimeError("boom")
        html = await _renderer()._render_saved_views_bar(
            _request(service, user=_user()), _STATE, "/admin/users", "/admin"
        )
        assert html == ""

    @pytest.mark.asyncio
    async def test_request_without_app_state_degrades_to_empty(self) -> None:
        request = SimpleNamespace(state=SimpleNamespace(user=_user()))
        html = await _renderer()._render_saved_views_bar(
            request, _STATE, "/admin/users", "/admin"
        )
        assert html == ""
