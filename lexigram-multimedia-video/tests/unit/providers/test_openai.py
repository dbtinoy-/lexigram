from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import VideoRequest
from lexigram.multimedia.video.exceptions import (
    VideoGenerationAuthenticationError,
    VideoGenerationError,
    VideoTimeoutError,
)
from lexigram.multimedia.video.providers.openai import OpenAIVideoProvider


def _mock_resp(status: int, body: str) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.text = AsyncMock(return_value=body)
    return mock_resp


@pytest.mark.asyncio
async def test_generate_submits_then_polls_until_completed() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=10)

    submit_cm = MagicMock()
    submit_cm.__aenter__ = AsyncMock(return_value=_mock_resp(200, '{"id": "vid-1"}'))
    submit_cm.__aexit__ = AsyncMock(return_value=False)

    poll_processing_cm = MagicMock()
    poll_processing_cm.__aenter__ = AsyncMock(
        return_value=_mock_resp(200, '{"status": "processing"}')
    )
    poll_processing_cm.__aexit__ = AsyncMock(return_value=False)

    poll_done_cm = MagicMock()
    poll_done_cm.__aenter__ = AsyncMock(
        return_value=_mock_resp(
            200, '{"status": "completed", "url": "https://cdn.example/v.mp4"}'
        )
    )
    poll_done_cm.__aexit__ = AsyncMock(return_value=False)

    calls = [poll_processing_cm, poll_done_cm]

    def poll_side_effect(*args: object, **kwargs: object) -> MagicMock:
        return calls.pop(0)

    with (
        patch("aiohttp.ClientSession.post", return_value=submit_cm),
        patch("aiohttp.ClientSession.get", side_effect=poll_side_effect),
    ):
        result = await provider.generate(VideoRequest(prompt="a drone over the valley"))

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.uri == "https://cdn.example/v.mp4"
    assert asset.mime_type == "video/mp4"
    assert asset.provider == "openai"


@pytest.mark.asyncio
async def test_generate_uses_configurable_base_url_and_model() -> None:
    provider = OpenAIVideoProvider(
        api_key="key",
        model="seedance-1",
        base_url="http://gateway.internal:8080",
        poll_interval=0.01,
        max_polls=5,
    )

    submit_cm = MagicMock()
    submit_cm.__aenter__ = AsyncMock(return_value=_mock_resp(200, '{"id": "vid-1"}'))
    submit_cm.__aexit__ = AsyncMock(return_value=False)

    poll_cm = MagicMock()
    poll_cm.__aenter__ = AsyncMock(
        return_value=_mock_resp(
            200, '{"status": "completed", "url": "https://cdn.example/v.mp4"}'
        )
    )
    poll_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("aiohttp.ClientSession.post", return_value=submit_cm) as mock_post,
        patch("aiohttp.ClientSession.get", return_value=poll_cm),
    ):
        await provider.generate(VideoRequest(prompt="a drone over the valley"))

    called_url = mock_post.call_args.args[0]
    assert called_url == "http://gateway.internal:8080/v1/videos"
    sent_payload = mock_post.call_args.kwargs["json"]
    assert sent_payload["model"] == "seedance-1"


@pytest.mark.asyncio
async def test_generate_returns_err_after_poll_budget_exhausted() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=2)

    submit_cm = MagicMock()
    submit_cm.__aenter__ = AsyncMock(return_value=_mock_resp(200, '{"id": "vid-1"}'))
    submit_cm.__aexit__ = AsyncMock(return_value=False)

    poll_cm = MagicMock()
    poll_cm.__aenter__ = AsyncMock(
        return_value=_mock_resp(200, '{"status": "processing"}')
    )
    poll_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("aiohttp.ClientSession.post", return_value=submit_cm),
        patch("aiohttp.ClientSession.get", return_value=poll_cm),
    ):
        result = await provider.generate(VideoRequest(prompt="a drone over the valley"))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoTimeoutError)


@pytest.mark.asyncio
async def test_generate_returns_err_on_submit_401() -> None:
    provider = OpenAIVideoProvider(api_key="bad", poll_interval=0.01, max_polls=2)

    submit_cm = MagicMock()
    submit_cm.__aenter__ = AsyncMock(return_value=_mock_resp(401, "unauthorized"))
    submit_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=submit_cm):
        result = await provider.generate(VideoRequest(prompt="a drone over the valley"))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationAuthenticationError)


@pytest.mark.asyncio
async def test_generate_returns_err_on_failed_job() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=10)

    submit_cm = MagicMock()
    submit_cm.__aenter__ = AsyncMock(return_value=_mock_resp(200, '{"id": "vid-1"}'))
    submit_cm.__aexit__ = AsyncMock(return_value=False)

    poll_cm = MagicMock()
    poll_cm.__aenter__ = AsyncMock(
        return_value=_mock_resp(200, '{"status": "failed", "error": "boom"}')
    )
    poll_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("aiohttp.ClientSession.post", return_value=submit_cm),
        patch("aiohttp.ClientSession.get", return_value=poll_cm),
    ):
        result = await provider.generate(VideoRequest(prompt="a drone over the valley"))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationError)
