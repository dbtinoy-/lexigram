"""Tests for Page ABC."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.pages.base import Page
from lexigram.admin.pages.types import NavigationEntry, PageResponse


class ConcretePage(Page):
    """Concrete page for testing."""

    title = "Test Page"
    path = "/test"

    async def view(self, request: Any) -> PageResponse:
        """Render test page."""
        return PageResponse(content="<h1>Test</h1>", title="Test Page")


class CustomPostPage(Page):
    """Page with custom post handler."""

    title = "Post Page"
    path = "/post"

    async def view(self, request: Any) -> PageResponse:
        """Render post page."""
        return PageResponse(content="<h1>Post</h1>", title="Post Page")

    async def post(self, request: Any) -> PageResponse:
        """Handle POST request."""
        return PageResponse(content="<h1>Posted</h1>", title="Post Page")


class PageWithNavigation(Page):
    """Page with navigation entry."""

    title = "Nav Page"
    path = "/nav"

    async def view(self, request: Any) -> PageResponse:
        """Render nav page."""
        return PageResponse(content="<h1>Nav</h1>", title="Nav Page")

    def navigation(self) -> NavigationEntry:
        """Return a navigation entry."""
        return NavigationEntry(label="Nav", url="/nav", icon="nav-icon")


class TestPageABC:
    """Tests for Page ABC."""

    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError):
            Page()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        page = ConcretePage()
        assert isinstance(page, Page)

    def test_title_attribute_set_on_subclass(self) -> None:
        page = ConcretePage()
        assert page.title == "Test Page"

    def test_path_defaults_to_empty_string(self) -> None:
        page = ConcretePage()
        assert page.path == "/test"

    def test_default_path_is_empty_string(self) -> None:
        class DefaultPathPage(Page):
            title = "Default"

            async def view(self, request: Any) -> PageResponse:
                return PageResponse(content="", title="Default")

        page = DefaultPathPage()
        assert page.path == ""

    def test_post_raises_method_not_allowed_by_default(self) -> None:
        page = ConcretePage()
        with pytest.raises(Exception) as exc_info:
            import asyncio

            asyncio.run(page.post(request=None))
        assert "not supported" in str(exc_info.value).lower() or "POST" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_custom_post_overrides_default(self) -> None:
        page = CustomPostPage()
        response = await page.post(request=None)
        assert response.title == "Post Page"
        assert response.content == "<h1>Posted</h1>"

    def test_navigation_returns_none_by_default(self) -> None:
        page = ConcretePage()
        assert page.navigation() is None

    def test_page_can_override_navigation(self) -> None:
        page = PageWithNavigation()
        entry = page.navigation()
        assert entry is not None
        assert entry.label == "Nav"
        assert entry.url == "/nav"
        assert entry.icon == "nav-icon"

    @pytest.mark.asyncio
    async def test_async_view_works_correctly(self) -> None:
        page = ConcretePage()
        response = await page.view(request=None)
        assert response.title == "Test Page"
        assert response.content == "<h1>Test</h1>"

    def test_isinstance_check_works(self) -> None:
        page = ConcretePage()
        assert isinstance(page, Page)
