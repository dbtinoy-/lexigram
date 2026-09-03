"""Tests for auth admin contributor and widgets."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import structlog.testing

from lexigram.auth.admin import (
    AuthAdminContributor,
)
from lexigram.contracts.admin.errors import WidgetNotFoundError
from lexigram.contracts.admin.types import WidgetParams, WidgetViewModel
from lexigram.contracts.admin.widget_content import StatContent
from lexigram.result import Ok


class TestAuthAdminContributor:
    """Tests for AuthAdminContributor."""

    @pytest.fixture
    def mock_handlers(self) -> dict[str, MagicMock]:
        """Create handlers returning StatContent directly."""
        active = MagicMock()
        active.get_data = AsyncMock(return_value=Ok(StatContent(stats=(MagicMock(),))))
        token = MagicMock()
        token.get_data = AsyncMock(return_value=Ok(StatContent(stats=(MagicMock(),))))
        failed = MagicMock()
        failed.get_data = AsyncMock(return_value=Ok(StatContent(stats=(MagicMock(),))))
        return {
            "active_sessions": active,
            "token_refresh_rate": token,
            "failed_logins": failed,
        }

    @pytest.fixture
    def contributor(self, mock_handlers: dict[str, MagicMock]) -> AuthAdminContributor:
        """Create an AuthAdminContributor instance with resolved handlers."""
        contributor = AuthAdminContributor()
        contributor._handlers = mock_handlers
        return contributor

    def test_contributor_metadata(self, contributor: AuthAdminContributor) -> None:
        """Test that contributor has correct metadata."""
        assert contributor.name == "auth"
        assert contributor.display_name == "Auth"
        assert contributor.group == "security"
        assert contributor.icon == "lock-closed"
        assert contributor.priority == 25

    def test_get_dashboard_widgets(self, contributor: AuthAdminContributor) -> None:
        """Test that contributor returns three dashboard widgets."""
        widgets = contributor.get_dashboard_widgets()
        assert len(widgets) == 3

        names = {w.name for w in widgets}
        assert "active_sessions" in names
        assert "token_refresh_rate" in names
        assert "failed_logins" in names

    def test_get_navigation_items(self, contributor: AuthAdminContributor) -> None:
        """Test that contributor returns navigation items."""
        nav_items = contributor.get_navigation_items()
        assert len(nav_items) >= 1
        assert nav_items[0].label == "Auth"

    def test_get_health_definitions(self, contributor: AuthAdminContributor) -> None:
        """Test that contributor returns health definitions."""
        health_defs = contributor.get_health_definitions()
        assert len(health_defs) >= 1

    def test_get_actions(self, contributor: AuthAdminContributor) -> None:
        """Test that contributor returns action definitions."""
        actions = contributor.get_actions()
        assert len(actions) >= 1

    @pytest.mark.asyncio
    async def test_render_widget_active_sessions(
        self,
        contributor: AuthAdminContributor,
        mock_handlers: dict[str, MagicMock],
    ) -> None:
        """Test rendering active_sessions widget."""
        params = WidgetParams()
        result = await contributor.render_widget("active_sessions", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert isinstance(vm.content, StatContent)
        mock_handlers["active_sessions"].get_data.assert_awaited_once_with(params)

    @pytest.mark.asyncio
    async def test_render_widget_token_refresh_rate(
        self,
        contributor: AuthAdminContributor,
        mock_handlers: dict[str, MagicMock],
    ) -> None:
        """Test rendering token_refresh_rate widget."""
        params = WidgetParams()
        result = await contributor.render_widget("token_refresh_rate", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert isinstance(vm.content, StatContent)
        mock_handlers["token_refresh_rate"].get_data.assert_awaited_once_with(params)

    @pytest.mark.asyncio
    async def test_render_widget_failed_logins(
        self,
        contributor: AuthAdminContributor,
        mock_handlers: dict[str, MagicMock],
    ) -> None:
        """Test rendering failed_logins widget."""
        params = WidgetParams()
        result = await contributor.render_widget("failed_logins", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert isinstance(vm.content, StatContent)
        mock_handlers["failed_logins"].get_data.assert_awaited_once_with(params)

    @pytest.mark.asyncio
    async def test_render_widget_not_found(
        self, contributor: AuthAdminContributor
    ) -> None:
        """Test that unknown widget returns error."""
        params = WidgetParams()
        result = await contributor.render_widget("nonexistent", params)

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, WidgetNotFoundError)
        assert "nonexistent" in str(error)

    @pytest.mark.asyncio
    async def test_render_widget_before_boot_returns_not_found(self) -> None:
        """Test that un-booted contributor returns WidgetNotFoundError."""
        contributor = AuthAdminContributor()
        params = WidgetParams()
        result = await contributor.render_widget("active_sessions", params)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), WidgetNotFoundError)


@pytest.mark.asyncio
async def test_missing_dependency_logs_contributor_as_disabled() -> None:
    """Expected auth-handler misses use one concise, structured event."""
    from unittest.mock import AsyncMock, MagicMock

    from lexigram.contracts.exceptions.container import UnresolvableDependencyError

    container = MagicMock()
    container.resolve = AsyncMock(
        side_effect=UnresolvableDependencyError(
            "[LEX_ERR_DI_004] missing\n  → Fix: register it",
            dependency="ActiveSessionsWidgetHandler",
        )
    )
    contributor = AuthAdminContributor()

    with structlog.testing.capture_logs() as captured:
        await contributor.on_admin_boot(container)

    disabled = [
        log for log in captured if log.get("event") == "admin.contributor_disabled"
    ]
    assert len(disabled) == 1
    assert disabled[0]["contributor"] == "auth"
    assert disabled[0]["feature"] == "widget handlers"
    assert disabled[0]["missing"] == "ActiveSessionsWidgetHandler"
    assert "LEX_ERR" not in str(disabled[0])
    assert "\n" not in str(disabled[0])


__all__ = [
    "TestAuthAdminContributor",
]
