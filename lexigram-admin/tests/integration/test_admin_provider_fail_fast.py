"""Verify resource-resolution failures fail fast in strict mode."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class _BrokenResource:
    """Resource class that will raise on resolution."""
    name = "broken"

    def __init__(self) -> None:
        raise RuntimeError("intentional breakage for test")


@pytest.fixture
def mock_app() -> MagicMock:
    app = MagicMock()
    app.state = MagicMock()
    return app


@pytest.mark.asyncio
async def test_strict_mode_raises_on_resource_resolution_failure(
    mock_app: MagicMock,
) -> None:
    """When strict_resource_resolution=True, a failure must propagate."""
    from lexigram.admin.config import AdminConfig
    from lexigram.admin.di.bundle_provider import AdminProvider
    from lexigram.di.container import Container

    config = AdminConfig(strict_resource_resolution=True)
    provider = AdminProvider(
        config=config,
        resources=[_BrokenResource],
    )
    container = Container()
    await provider.register(container)
    await provider.boot(container)
    with pytest.raises(RuntimeError, match="intentional breakage"):
        await provider.mount_to_app(mock_app, container)


@pytest.mark.asyncio
async def test_permissive_mode_swallows_resource_resolution_failure(
    mock_app: MagicMock,
) -> None:
    """When strict_resource_resolution=False, a failure must be logged but not raised."""
    from lexigram.admin.config import AdminConfig
    from lexigram.admin.di.bundle_provider import AdminProvider
    from lexigram.di.container import Container

    config = AdminConfig(strict_resource_resolution=False)
    provider = AdminProvider(
        config=config,
        resources=[_BrokenResource],
    )
    container = Container()
    await provider.register(container)
    await provider.boot(container)
    # Should not raise
    await provider.mount_to_app(mock_app, container)
