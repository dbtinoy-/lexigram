import pytest

from lexigram.contracts.multimedia.types import (
    ImageRequest,
    MediaAsset,
    MusicRequest,
    TTSRequest,
    UpscaleRequest,
    VideoRequest,
)


def test_media_asset_with_bytes_has_no_uri() -> None:
    asset = MediaAsset(mime_type="audio/mpeg", provider="local-http", bytes_data=b"abc")
    assert asset.has_bytes is True
    assert asset.has_uri is False


def test_media_asset_with_uri_has_no_bytes() -> None:
    asset = MediaAsset(mime_type="audio/mpeg", provider="elevenlabs", uri="https://example/x.mp3")
    assert asset.has_uri is True
    assert asset.has_bytes is False


def test_media_asset_is_frozen() -> None:
    asset = MediaAsset(mime_type="audio/mpeg", provider="local-http", bytes_data=b"abc")
    with pytest.raises(Exception):  # noqa: B017 — frozen dataclass raises FrozenInstanceError
        asset.provider = "other"  # type: ignore[misc]


def test_tts_request_defaults() -> None:
    req = TTSRequest(text="hello")
    assert req.voice is None
    assert req.format == "mp3"


def test_music_request_defaults() -> None:
    req = MusicRequest(prompt="lofi beat")
    assert req.duration_seconds == 30.0


def test_video_request_defaults() -> None:
    req = VideoRequest(prompt="a cat")
    assert req.duration_seconds == 4.0
    assert req.resolution == "1280x720"


def test_image_request_defaults() -> None:
    req = ImageRequest(prompt="a cat")
    assert req.width == 1024
    assert req.height == 1024


def test_upscale_request_defaults() -> None:
    asset = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"x")
    req = UpscaleRequest(asset=asset)
    assert req.scale_factor == 4
    assert req.extra == {}
