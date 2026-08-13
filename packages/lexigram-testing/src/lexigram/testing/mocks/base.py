from __future__ import annotations

from lexigram.di.container import Container
from lexigram.di.provider import Provider
from lexigram.di.types import ProviderPriority


class MockProvider(Provider):
    """Base class for mock providers in testing."""

    name: str = "mock"
    priority: ProviderPriority = ProviderPriority.DOMAIN

    def __init__(self) -> None:
        super().__init__()
        self._started = False
        self._stopped = False

    async def register(self, container: Container) -> None:  # type: ignore[override]
        """No-op register for mock providers."""

    async def boot(self, container: Container) -> None:  # type: ignore[override]
        self._started = True

    async def shutdown(self) -> None:
        self._stopped = True

    @property
    def started(self) -> bool:
        return self._started

    @property
    def stopped(self) -> bool:
        return self._stopped
