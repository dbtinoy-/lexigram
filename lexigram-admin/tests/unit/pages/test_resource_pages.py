"""Tests for resource pages (ListPage, CreatePage, EditPage, ViewPage)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.admin.pages.base import MethodNotAllowedError, Page
from lexigram.admin.pages.resource_pages import (
    CreatePage,
    EditPage,
    ListPage,
    ViewPage,
)
from lexigram.admin.pages.types import PageResponse


class TestListPage:
    """Tests for ListPage."""

    def test_can_be_created_with_resource_name(self) -> None:
        page = ListPage(resource_name="users")
        assert page.resource_name == "users"

    def test_default_title_is_list(self) -> None:
        page = ListPage(resource_name="users")
        assert page.title == "List"

    @pytest.mark.asyncio
    async def test_view_returns_page_response(self) -> None:
        page = ListPage(resource_name="users")
        request = MagicMock()
        response = await page.view(request)
        assert isinstance(response, PageResponse)
        assert response.title == "List"
        assert "users" in response.content

    @pytest.mark.asyncio
    async def test_view_renders_list_html(self) -> None:
        page = ListPage(resource_name="posts")
        request = MagicMock()
        response = await page.view(request)
        assert "<div>List of posts</div>" in response.content

    def test_path_can_be_set_via_constructor(self) -> None:
        page = ListPage(resource_name="users", path="/admin/users")
        assert page.path == "/admin/users"

    def test_path_defaults_to_empty_string(self) -> None:
        page = ListPage(resource_name="users")
        assert page.path == ""


class TestCreatePage:
    """Tests for CreatePage."""

    def test_can_be_created_with_resource_name(self) -> None:
        page = CreatePage(resource_name="users")
        assert page.resource_name == "users"

    def test_default_title_is_create(self) -> None:
        page = CreatePage(resource_name="users")
        assert page.title == "Create"

    @pytest.mark.asyncio
    async def test_view_returns_page_response_with_form(self) -> None:
        page = CreatePage(resource_name="users")
        request = MagicMock()
        response = await page.view(request)
        assert isinstance(response, PageResponse)
        assert response.title == "Create"
        assert "form" in response.content
        assert "users" in response.content

    @pytest.mark.asyncio
    async def test_post_handles_form_submission(self) -> None:
        page = CreatePage(resource_name="users")
        request = MagicMock()
        response = await page.post(request)
        assert isinstance(response, PageResponse)
        assert "Created" in response.content
        assert "users" in response.content

    @pytest.mark.asyncio
    async def test_view_and_post_both_return_valid_page_response(self) -> None:
        page = CreatePage(resource_name="products")
        request = MagicMock()
        view_response = await page.view(request)
        post_response = await page.post(request)
        assert view_response.title == "Create"
        assert post_response.title == "Create"
        assert "products" in view_response.content
        assert "products" in post_response.content


class TestEditPage:
    """Tests for EditPage."""

    def test_can_be_created_with_resource_name(self) -> None:
        page = EditPage(resource_name="users")
        assert page.resource_name == "users"

    def test_default_title_is_edit(self) -> None:
        page = EditPage(resource_name="users")
        assert page.title == "Edit"

    @pytest.mark.asyncio
    async def test_view_extracts_record_id_from_path_params(self) -> None:
        page = EditPage(resource_name="users")
        request = MagicMock()
        request.path_params = {"id": "42"}
        response = await page.view(request)
        assert "#42" in response.content

    @pytest.mark.asyncio
    async def test_view_handles_missing_path_params(self) -> None:
        page = EditPage(resource_name="users")
        request = MagicMock()
        del request.path_params
        response = await page.view(request)
        assert isinstance(response, PageResponse)

    @pytest.mark.asyncio
    async def test_post_handles_update_submission(self) -> None:
        page = EditPage(resource_name="users")
        request = MagicMock()
        request.path_params = {"id": "7"}
        response = await page.post(request)
        assert isinstance(response, PageResponse)
        assert "Updated" in response.content
        assert "#7" in response.content

    @pytest.mark.asyncio
    async def test_render_form_includes_record_id(self) -> None:
        page = EditPage(resource_name="users")
        form = page._render_form(MagicMock(), "99")
        assert "#99" in form
        assert "Edit" in form
        assert "users" in form


class TestViewPage:
    """Tests for ViewPage."""

    def test_can_be_created_with_resource_name(self) -> None:
        page = ViewPage(resource_name="users")
        assert page.resource_name == "users"

    def test_default_title_is_view(self) -> None:
        page = ViewPage(resource_name="users")
        assert page.title == "View"

    @pytest.mark.asyncio
    async def test_view_returns_page_response_with_breadcrumbs(self) -> None:
        page = ViewPage(resource_name="users")
        request = MagicMock()
        response = await page.view(request)
        assert isinstance(response, PageResponse)
        assert response.breadcrumbs is not None

    @pytest.mark.asyncio
    async def test_breadcrumbs_include_home_and_resource_name(self) -> None:
        page = ViewPage(resource_name="users")
        request = MagicMock()
        response = await page.view(request)
        assert response.breadcrumbs is not None
        labels = [b[0] for b in response.breadcrumbs]
        assert "Home" in labels
        assert "users" in labels
        assert "View" in labels

    @pytest.mark.asyncio
    async def test_render_detail_includes_record_id(self) -> None:
        page = ViewPage(resource_name="users")
        request = MagicMock()
        request.path_params = {"id": "123"}
        response = await page.view(request)
        assert "#123" in response.content
        assert "users" in response.content


class TestAllResourcePages:
    """Tests common to all resource pages."""

    @pytest.mark.asyncio
    async def test_all_are_instances_of_page(self) -> None:
        list_page = ListPage(resource_name="users")
        create_page = CreatePage(resource_name="users")
        edit_page = EditPage(resource_name="users")
        view_page = ViewPage(resource_name="users")
        assert isinstance(list_page, Page)
        assert isinstance(create_page, Page)
        assert isinstance(edit_page, Page)
        assert isinstance(view_page, Page)

    @pytest.mark.asyncio
    async def test_list_page_raises_method_not_allowed_for_post(self) -> None:
        page = ListPage(resource_name="users")
        request = MagicMock()
        with pytest.raises(MethodNotAllowedError):
            await page.post(request)

    @pytest.mark.asyncio
    async def test_view_page_raises_method_not_allowed_for_post(self) -> None:
        page = ViewPage(resource_name="users")
        request = MagicMock()
        with pytest.raises(MethodNotAllowedError):
            await page.post(request)

    @pytest.mark.asyncio
    async def test_create_page_does_not_raise_for_post(self) -> None:
        page = CreatePage(resource_name="users")
        request = MagicMock()
        response = await page.post(request)
        assert response.title == "Create"

    @pytest.mark.asyncio
    async def test_edit_page_does_not_raise_for_post(self) -> None:
        page = EditPage(resource_name="users")
        request = MagicMock()
        response = await page.post(request)
        assert response.title == "Edit"
