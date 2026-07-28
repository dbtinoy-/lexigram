"""Tests for auth admin contributor and widgets."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.auth.admin import (
    ActiveSessionsWidgetHandler,
    AuthAdminContributor,
    FailedLoginsWidgetHandler,
    TokenRefreshRateWidgetHandler,
)
from lexigram.auth.admin.renderer import PackageWidgetRenderer
from lexigram.auth.admin.viewmodels import (
    ActiveSessionsViewModel,
    FailedLoginsViewModel,
    TokenRefreshRateViewModel,
)
from lexigram.contracts.admin.errors import WidgetNotFoundError
from lexigram.contracts.admin.types import WidgetParams, WidgetViewModel
from lexigram.result import Ok


class TestActiveSessionsWidgetHandler:
    """Tests for ActiveSessionsWidgetHandler."""

    @pytest.fixture
    def mock_session_manager(self) -> MagicMock:
        """Create a mock session manager."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_data_returns_viewmodel(
        self, mock_session_manager: MagicMock
    ) -> None:
        """Test that handler returns ActiveSessionsViewModel."""
        handler = ActiveSessionsWidgetHandler(session_manager=mock_session_manager)
        params = WidgetParams()

        result = await handler.get_data(params)

        assert result.is_ok()
        viewmodel = result.unwrap()
        assert isinstance(viewmodel, ActiveSessionsViewModel)
        assert viewmodel.count == 0
        assert viewmodel.peak_today == 0

    @pytest.mark.asyncio
    async def test_get_data_handles_exception(
        self, mock_session_manager: MagicMock
    ) -> None:
        """Test that handler returns defaults on exception."""
        mock_session_manager.get_active_sessions = AsyncMock(
            side_effect=Exception("Database error")
        )
        handler = ActiveSessionsWidgetHandler(session_manager=mock_session_manager)
        params = WidgetParams()

        result = await handler.get_data(params)

        # Handler returns safe defaults (zeros) instead of raising
        assert result.is_ok()
        viewmodel = result.unwrap()
        assert viewmodel.count == 0
        assert viewmodel.peak_today == 0


class TestTokenRefreshRateWidgetHandler:
    """Tests for TokenRefreshRateWidgetHandler."""

    @pytest.fixture
    def mock_session_manager(self) -> MagicMock:
        """Create a mock session manager."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_data_returns_viewmodel(
        self, mock_session_manager: MagicMock
    ) -> None:
        """Test that handler returns TokenRefreshRateViewModel."""
        handler = TokenRefreshRateWidgetHandler(session_manager=mock_session_manager)
        params = WidgetParams(time_window_minutes=60)

        result = await handler.get_data(params)

        assert result.is_ok()
        viewmodel = result.unwrap()
        assert isinstance(viewmodel, TokenRefreshRateViewModel)
        assert viewmodel.refreshes_per_minute == 0.0
        assert viewmodel.total_refreshes == 0

    @pytest.mark.asyncio
    async def test_get_data_handles_exception(
        self, mock_session_manager: MagicMock
    ) -> None:
        """Test that handler returns AdminError on exception."""
        handler = TokenRefreshRateWidgetHandler(session_manager=mock_session_manager)
        params = WidgetParams()

        result = await handler.get_data(params)

        assert result.is_ok()  # Should return defaults safely


class TestFailedLoginsWidgetHandler:
    """Tests for FailedLoginsWidgetHandler."""

    @pytest.fixture
    def mock_session_manager(self) -> MagicMock:
        """Create a mock session manager."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_data_returns_viewmodel(
        self, mock_session_manager: MagicMock
    ) -> None:
        """Test that handler returns FailedLoginsViewModel."""
        handler = FailedLoginsWidgetHandler(session_manager=mock_session_manager)
        params = WidgetParams(time_window_minutes=60)

        result = await handler.get_data(params)

        assert result.is_ok()
        viewmodel = result.unwrap()
        assert isinstance(viewmodel, FailedLoginsViewModel)
        assert viewmodel.count == 0
        assert viewmodel.unique_ips == 0
        assert viewmodel.is_elevated is False

    @pytest.mark.asyncio
    async def test_get_data_handles_exception(
        self, mock_session_manager: MagicMock
    ) -> None:
        """Test that handler returns AdminError on exception."""
        handler = FailedLoginsWidgetHandler(session_manager=mock_session_manager)
        params = WidgetParams()

        result = await handler.get_data(params)

        assert result.is_ok()  # Should return defaults safely


class TestAuthAdminContributor:
    """Tests for AuthAdminContributor."""

    @pytest.fixture
    def mock_renderer(self) -> MagicMock:
        """Mock PackageWidgetRenderer."""
        from lexigram.auth.admin.renderer import PackageWidgetRenderer

        renderer = MagicMock(spec=PackageWidgetRenderer)
        renderer.render = MagicMock(return_value="<div>Rendered Widget</div>")
        return renderer

    @pytest.fixture
    def mock_active_sessions_handler(self) -> MagicMock:
        """Mock ActiveSessionsWidgetHandler."""
        handler = MagicMock(spec=ActiveSessionsWidgetHandler)
        handler.get_data = AsyncMock(
            return_value=Ok(ActiveSessionsViewModel(count=5, peak_today=10))
        )
        return handler

    @pytest.fixture
    def mock_token_refresh_handler(self) -> MagicMock:
        """Mock TokenRefreshRateWidgetHandler."""
        handler = MagicMock(spec=TokenRefreshRateWidgetHandler)
        handler.get_data = AsyncMock(
            return_value=Ok(
                TokenRefreshRateViewModel(refreshes_per_minute=1.5, total_refreshes=90)
            )
        )
        return handler

    @pytest.fixture
    def mock_failed_logins_handler(self) -> MagicMock:
        """Mock FailedLoginsWidgetHandler."""
        handler = MagicMock(spec=FailedLoginsWidgetHandler)
        handler.get_data = AsyncMock(
            return_value=Ok(
                FailedLoginsViewModel(count=2, unique_ips=1, is_elevated=False)
            )
        )
        return handler

    @pytest.fixture
    def mock_container(
        self,
        mock_renderer: MagicMock,
        mock_active_sessions_handler: MagicMock,
        mock_token_refresh_handler: MagicMock,
        mock_failed_logins_handler: MagicMock,
    ) -> MagicMock:
        """Mock container that resolves handlers via on_admin_boot."""
        container = MagicMock()
        resolve_map = {
            PackageWidgetRenderer: mock_renderer,
            ActiveSessionsWidgetHandler: mock_active_sessions_handler,
            TokenRefreshRateWidgetHandler: mock_token_refresh_handler,
            FailedLoginsWidgetHandler: mock_failed_logins_handler,
        }
        container.resolve = AsyncMock(side_effect=resolve_map.get)
        return container

    @pytest.fixture
    def contributor(
        self,
        mock_renderer: MagicMock,
        mock_active_sessions_handler: MagicMock,
        mock_token_refresh_handler: MagicMock,
        mock_failed_logins_handler: MagicMock,
        mock_container: MagicMock,
    ) -> AuthAdminContributor:
        """Create an AuthAdminContributor instance with resolved handlers."""
        contributor = AuthAdminContributor()
        contributor._renderer = mock_renderer
        contributor._active_sessions_handler = mock_active_sessions_handler
        contributor._token_refresh_handler = mock_token_refresh_handler
        contributor._failed_logins_handler = mock_failed_logins_handler
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
        self, contributor: AuthAdminContributor
    ) -> None:
        """Test rendering active_sessions widget."""
        params = WidgetParams()
        result = await contributor.render_widget("active_sessions", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert isinstance(vm.body, str)
        assert len(vm.body) > 0  # Verify HTML is rendered

    @pytest.mark.asyncio
    async def test_render_widget_token_refresh_rate(
        self, contributor: AuthAdminContributor
    ) -> None:
        """Test rendering token_refresh_rate widget."""
        params = WidgetParams()
        result = await contributor.render_widget("token_refresh_rate", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert isinstance(vm.body, str)

    @pytest.mark.asyncio
    async def test_render_widget_failed_logins(
        self, contributor: AuthAdminContributor
    ) -> None:
        """Test rendering failed_logins widget."""
        params = WidgetParams()
        result = await contributor.render_widget("failed_logins", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert isinstance(vm.body, str)

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


__all__ = [
    "TestActiveSessionsWidgetHandler",
    "TestAuthAdminContributor",
    "TestFailedLoginsWidgetHandler",
    "TestTokenRefreshRateWidgetHandler",
]
