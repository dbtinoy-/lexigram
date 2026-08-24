"""Tests for ApplicationLifecycle collaborator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.app.base import Application, AppState
from lexigram.app.lifecycle import ApplicationLifecycle


class TestApplicationLifecycleInstantiation:
    """ApplicationLifecycle should be instantiable with required dependencies."""

    def test_creates_with_container_and_orchestrator(self) -> None:
        """Should accept container, orchestrator, config, logger, and app_name."""
        from lexigram.config import LexigramConfig
        from lexigram.di.container import Container
        from lexigram.di.orchestrator import ProviderOrchestrator
        from lexigram.logging import get_logger

        container = Container()
        orchestrator = ProviderOrchestrator(container)
        config = LexigramConfig()
        logger = get_logger("test")

        lifecycle = ApplicationLifecycle(
            container=container,
            orchestrator=orchestrator,
            config=config,
            logger=logger,
            app_name="test-app",
        )

        assert lifecycle is not None
        assert lifecycle._app_name == "test-app"


class TestApplicationLifecycleBoot:
    """ApplicationLifecycle.boot should orchestrate provider boot sequence."""

    @pytest.mark.asyncio
    async def test_boot_sets_start_time(self) -> None:
        """Boot should record start time for uptime tracking."""
        from lexigram.config import LexigramConfig
        from lexigram.di.container import Container
        from lexigram.di.orchestrator import ProviderOrchestrator
        from lexigram.logging import get_logger

        container = Container()
        orchestrator = ProviderOrchestrator(container)
        config = LexigramConfig()
        logger = get_logger("test")

        lifecycle = ApplicationLifecycle(
            container=container,
            orchestrator=orchestrator,
            config=config,
            logger=logger,
            app_name="test-app",
        )

        await lifecycle.boot()

        assert lifecycle._start_time is not None

    @pytest.mark.asyncio
    async def test_boot_calls_orchestrator_boot_all(self) -> None:
        """Boot should delegate to orchestrator.boot_all."""
        from lexigram.config import LexigramConfig
        from lexigram.di.container import Container
        from lexigram.di.orchestrator import ProviderOrchestrator
        from lexigram.logging import get_logger

        container = Container()
        orchestrator = ProviderOrchestrator(container)
        config = LexigramConfig()
        logger = get_logger("test")

        lifecycle = ApplicationLifecycle(
            container=container,
            orchestrator=orchestrator,
            config=config,
            logger=logger,
            app_name="test-app",
        )

        orchestrator.boot_all = AsyncMock()

        await lifecycle.boot()

        orchestrator.boot_all.assert_awaited_once_with(container)


class TestApplicationLifecycleShutdown:
    """ApplicationLifecycle.shutdown should orchestrate provider shutdown."""

    @pytest.mark.asyncio
    async def test_shutdown_disposes_container(self) -> None:
        """Shutdown should dispose the container."""
        from lexigram.config import LexigramConfig
        from lexigram.di.container import Container
        from lexigram.di.orchestrator import ProviderOrchestrator
        from lexigram.logging import get_logger

        container = Container()
        orchestrator = ProviderOrchestrator(container)
        config = LexigramConfig()
        logger = get_logger("test")

        lifecycle = ApplicationLifecycle(
            container=container,
            orchestrator=orchestrator,
            config=config,
            logger=logger,
            app_name="test-app",
        )

        container.dispose = AsyncMock()

        await lifecycle.shutdown()

        container.dispose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_calculates_uptime(self) -> None:
        """Shutdown should calculate uptime from start_time."""
        from lexigram.config import LexigramConfig
        from lexigram.di.container import Container
        from lexigram.di.orchestrator import ProviderOrchestrator
        from lexigram.logging import get_logger

        container = Container()
        orchestrator = ProviderOrchestrator(container)
        config = LexigramConfig()
        logger = get_logger("test")

        lifecycle = ApplicationLifecycle(
            container=container,
            orchestrator=orchestrator,
            config=config,
            logger=logger,
            app_name="test-app",
        )

        lifecycle._start_time = 100.0

        await lifecycle.shutdown()

        assert lifecycle._uptime_seconds is not None
        assert lifecycle._uptime_seconds >= 0


class TestApplicationDelegatesToLifecycle:
    """Application should delegate boot/shutdown to ApplicationLifecycle."""

    @pytest.mark.asyncio
    async def test_application_uses_lifecycle_for_start(self) -> None:
        """Application.start should delegate to lifecycle.boot."""
        app = Application()

        with patch.object(app._lifecycle, "boot", new_callable=AsyncMock) as mock_boot:
            await app.start()

            mock_boot.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_application_uses_lifecycle_for_stop(self) -> None:
        """Application.stop should delegate to lifecycle.shutdown."""
        app = Application()
        app._state = AppState.RUNNING

        with patch.object(
            app._lifecycle, "shutdown", new_callable=AsyncMock
        ) as mock_shutdown:
            await app.stop()

            mock_shutdown.assert_awaited_once()
