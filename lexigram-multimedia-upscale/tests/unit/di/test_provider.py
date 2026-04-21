import pytest

from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import UpscaleProvider
from lexigram.multimedia.upscale.config import UpscaleConfig
from lexigram.multimedia.upscale.di.provider import UpscaleGenerationProvider
from lexigram.multimedia.upscale.providers.real_esrgan import RealEsrganUpscaleProvider


class _FakeContainer:
    def __init__(self) -> None:
        self.bindings: dict[object, object] = {}

    def singleton(self, key: object, value: object) -> None:
        self.bindings[key] = value

    async def resolve(self, key: object) -> object:
        if key not in self.bindings:
            raise LookupError(key)
        return self.bindings[key]


@pytest.mark.asyncio
async def test_register_binds_real_esrgan_backend_by_default() -> None:
    provider = UpscaleGenerationProvider(config=UpscaleConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[UpscaleProvider]
    assert isinstance(bound, RealEsrganUpscaleProvider)


@pytest.mark.asyncio
async def test_health_check_reports_healthy_after_register() -> None:
    provider = UpscaleGenerationProvider(config=UpscaleConfig())
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.component == "upscale"


@pytest.mark.asyncio
async def test_unknown_backend_raises_not_installed() -> None:
    provider = UpscaleGenerationProvider(
        config=UpscaleConfig(backend="unknown")  # type: ignore[arg-type]
    )
    container = _FakeContainer()

    with pytest.raises(ProviderNotInstalledError):
        await provider.register(container)
