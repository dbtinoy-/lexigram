"""Tests for application lifecycle management"""

from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import pytest

from lexigram.app import run_application, start_application, stop_application
from lexigram.app.base import Application
from lexigram.di.container import Container
from lexigram.di.types import ProviderPriority


async def _await_tasks(*tasks, **kwargs):
    """Helper to await a sequence of coroutines in tests without calling asyncio.gather.
    This avoids hitting patches of asyncio.gather in tests while still executing the
    provider coroutines so they don't become unawaited."""
    results = []
    for t in tasks:
        try:
            results.append(await t)
        except (RuntimeError, ValueError, TypeError, ConnectionError) as e:
            results.append(e)
    return results


from lexigram.testing.mocks import MockProvider as BaseMockProvider


class MockProvider(BaseMockProvider):
    """Mock provider for testing (thin subclass of central MockProvider)

    This preserves the test's spy-style behavior while reusing the canonical
    mock provider implementation to avoid duplication across tests.
    """

    name = "mock"
    priority = ProviderPriority.DOMAIN

    def __init__(self):
        super().__init__()
        self.register_called = False
        self.boot_called = False
        self.shutdown_called = False
        self.startup_called = False
        self.shutdown_called = False

        # Use regular Mocks for methods to avoid coroutine warnings
        self._register_mock = Mock(side_effect=self._mock_register)
        self._startup_mock = Mock(side_effect=self._mock_startup)
        self._shutdown_mock = Mock(side_effect=self._mock_shutdown)
        self._health_check_mock = Mock(return_value={"status": "healthy"})

    async def register(self, container: Container) -> None:
        self._register_mock(container)

    async def boot(self, app: Application) -> None:
        self._startup_mock(app)
        self.boot_called = True

    async def shutdown(self) -> None:
        self._shutdown_mock(app)
        self.shutdown_called = True

    async def health_check(self) -> dict:
        return self._health_check_mock()

    def _mock_register(self, container: Container) -> None:
        """Mock register method"""
        self.register_called = True

    def _mock_startup(self, app: Application) -> None:
        """Mock startup method"""
        self.startup_called = True

    def _mock_shutdown(self, app: Application) -> None:
        """Mock shutdown method"""
        self.shutdown_called = True


class MockModule:
    """Mock module for testing"""

    def __init__(self, name: str = "mock_module"):
        self.name = name
        self.providers = []
        self.shutdown_providers_called = False

    async def shutdown_providers(self, app: Application) -> None:
        """Mock shutdown providers"""
        self.shutdown_providers_called = True


@pytest.fixture
def mock_app():
    """Create a mock application for testing"""
    app = MagicMock(spec=Application)
    app.name = "test-app"
    # mock_app.started property needs to return value of _started
    # But since we are mocking, we can just use a PropertyMock or simple attribute if we don't mock the property
    # Let's just set .started as a property
    type(app).started = PropertyMock(return_value=False)

    app._started = False  # For legacy checks if any
    app.providers = []
    app.module_names = []
    app._initialized_modules = []

    # Make start/stop AsyncMocks so they can be awaited
    app.start = AsyncMock()
    app.stop = AsyncMock()

    app.container = MagicMock(spec=Container)
    app.container_builder = MagicMock()
    app.initialize_modules = AsyncMock(return_value=[])
    app.logger = MagicMock()
    return app


@pytest.fixture
def mock_provider():
    """Fixture that returns a MockProvider instance."""
    return MockProvider()


class TestStartApplication:
    """Test start_application function"""

    @pytest.mark.asyncio
    async def test_start_application_already_started(self, mock_app):
        """Test starting an already started application"""
        # mock_app._started = True
        type(mock_app).started = PropertyMock(return_value=True)
        # We need _started to be True for the logic in start_application (which checks app._started??
        # No, start_application now calls app.start(). logic is inside app.start())
        # But here we are mocking app.start(). So we just verify it is called.

        await start_application(mock_app)

        mock_app.start.assert_called_once()
        # The logic of returning early is inside app.start(), which is mocked here.
        # So this test is essentially verifying delegation.

    @pytest.mark.asyncio
    async def test_start_application_success(self, mock_app, mock_provider):
        """Test successful application startup"""
        await start_application(mock_app)

        mock_app.start.assert_called_once()
        # Note: We don't check logging here anymore because logging is done inside app.start()
        # which is mocked.

    @pytest.mark.asyncio
    async def test_start_application_failure(self, mock_app):
        """Test application startup failure"""
        mock_app.start.side_effect = Exception("Startup failed")

        with pytest.raises(
            Exception,
        ):  # The wrapper catches Exception and raises LexigramError
            await start_application(mock_app)


class TestStopApplication:
    """Test stop_application function"""

    @pytest.mark.asyncio
    async def test_stop_application_success(self, mock_app):
        """Test successful application shutdown"""
        await stop_application(mock_app)
        mock_app.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_application_failure(self, mock_app):
        """Test application shutdown failure"""
        mock_app.stop.side_effect = Exception("Shutdown failed")

        with pytest.raises(Exception):
            await stop_application(mock_app)


class TestRunApplication:
    """Test run_application function"""

    @pytest.mark.asyncio
    async def test_run_application_keyboard_interrupt(self, mock_app):
        """Test run_application handles KeyboardInterrupt"""

        # Patch at the module where the function is defined so the call
        # inside run_application is intercepted correctly.
        with (
            patch(
                "lexigram.app.runner.start_application", new_callable=AsyncMock,
            ) as mock_start,
            patch(
                "lexigram.app.runner.stop_application", new_callable=AsyncMock,
            ),
        ):
            mock_start.side_effect = KeyboardInterrupt()

            # Should not raise — KeyboardInterrupt is caught inside run_application
            await run_application(mock_app)

            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_application_exception(self, mock_app):
        """Test run_application handles exceptions"""
        with (
            patch(
                "lexigram.app.runner.start_application", new_callable=AsyncMock,
            ) as mock_start,
            patch(
                "lexigram.app.runner.stop_application", new_callable=AsyncMock,
            ),
        ):
            mock_start.side_effect = Exception("Application error")

            with pytest.raises(Exception):
                await run_application(mock_app)

    @pytest.mark.asyncio
    async def test_run_application_calls_start_and_stops(self, mock_app):
        """Test run_application calls start and stop properly"""

        with (
            patch(
                "lexigram.app.runner.start_application", new_callable=AsyncMock,
            ) as mock_start,
            patch(
                "lexigram.app.runner.stop_application", new_callable=AsyncMock,
            ) as mock_stop,
            patch("asyncio.Event.wait", new_callable=AsyncMock) as mock_wait,
        ):
            # Make Event.wait raise KeyboardInterrupt to exit the wait call
            mock_wait.side_effect = KeyboardInterrupt()

            await run_application(mock_app)

            mock_start.assert_called_once_with(mock_app)
            # stop should be called in finally block
            mock_stop.assert_called_once_with(mock_app)
