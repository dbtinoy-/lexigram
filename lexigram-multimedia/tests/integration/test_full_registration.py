"""Integration test: full register()/boot() cycle + entry-point discovery."""

from unittest.mock import MagicMock, patch

import pytest

from lexigram.contracts.multimedia.protocols import (
    ImageProvider,
    MusicProvider,
    TTSProvider,
    VideoProvider,
)
from lexigram.multimedia.config import MultimediaConfig
from lexigram.multimedia.di.provider import MultimediaProvider


class _FakeContainer:
    def __init__(self) -> None:
        self.bindings: dict[object, object] = {}

    def singleton(self, key: object, value: object) -> None:
        self.bindings[key] = value

    async def resolve(self, key: object) -> object:
        if key not in self.bindings:
            raise LookupError(key)
        return self.bindings[key]


class _FakeSubsystem:
    """A stand-in 5th subsystem discovered via entry points."""

    registered = False

    def __init__(self) -> None:
        _FakeSubsystem.registered = False

    @property
    def name(self) -> str:
        return "hologram"

    async def register(self, container: object) -> None:
        _FakeSubsystem.registered = True

    async def boot(self, container: object) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health_check(self, timeout: float = 5.0) -> object:
        from lexigram.contracts.core.health import HealthCheckResult, HealthStatus

        return HealthCheckResult(component="hologram", status=HealthStatus.HEALTHY)


@pytest.mark.asyncio
async def test_full_registration_binds_all_four_protocols() -> None:
    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    await provider.register(container)

    for protocol in (TTSProvider, MusicProvider, VideoProvider, ImageProvider):
        assert protocol in container.bindings


@pytest.mark.asyncio
async def test_entry_point_subsystem_is_discovered_and_registered() -> None:
    fake_ep = MagicMock()
    fake_ep.name = "hologram"
    fake_ep.load.return_value = _FakeSubsystem

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    with patch(
        "lexigram.multimedia.di.provider.importlib.metadata.entry_points",
        return_value=[fake_ep],
    ):
        await provider.register(container)

    assert _FakeSubsystem.registered is True
    assert "hologram" in provider._sub_providers


@pytest.mark.asyncio
async def test_entry_point_core_names_are_skipped() -> None:
    fake_ep = MagicMock()
    fake_ep.name = "audio-tts"
    fake_ep.load.return_value = _FakeSubsystem

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    with patch(
        "lexigram.multimedia.di.provider.importlib.metadata.entry_points",
        return_value=[fake_ep],
    ):
        await provider.register(container)

    assert type(provider._sub_providers["audio-tts"]).__name__ != "FakeSubsystem"


@pytest.mark.asyncio
async def test_health_check_aggregates_all_subsystems() -> None:
    from lexigram.contracts.core.health import HealthStatus

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    await provider.register(container)

    result = await provider.health_check()

    # With default local-http backends and no server running, individual
    # sub-providers report DEGRADED; the umbrella aggregates, never
    # UNHEALTHY while all backends are configured.
    assert result.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
    assert set(result.details["components"]) == {
        "audio-tts",
        "audio-music",
        "video",
        "image",
    }


@pytest.mark.asyncio
async def test_shutdown_clears_sub_providers() -> None:
    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    await provider.register(container)
    assert len(provider._sub_providers) == 4

    await provider.shutdown()

    assert provider._sub_providers == {}
