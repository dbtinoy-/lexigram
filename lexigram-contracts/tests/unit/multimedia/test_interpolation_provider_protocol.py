from lexigram.contracts.core.result import Ok, Result
from lexigram.contracts.multimedia.exceptions import MultimediaError
from lexigram.contracts.multimedia.protocols import InterpolationProvider
from lexigram.contracts.multimedia.types import InterpolationRequest, MediaAsset


class _FakeInterpolationProvider:
    async def interpolate(self, request):
        asset = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"mid")
        return Ok(asset)


async def test_fake_provider_satisfies_protocol() -> None:
    provider: InterpolationProvider = _FakeInterpolationProvider()
    frame_a = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"a")
    frame_b = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"b")
    result: Result[MediaAsset, MultimediaError] = await provider.interpolate(
        InterpolationRequest(frame_a=frame_a, frame_b=frame_b)
    )
    assert result.is_ok()


def test_isinstance_check_via_runtime_checkable() -> None:
    assert isinstance(_FakeInterpolationProvider(), InterpolationProvider)
