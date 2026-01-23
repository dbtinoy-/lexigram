import inspect

from lexigram.contracts.core.result import Ok, Result
from lexigram.contracts.multimedia.exceptions import VideoGenerationError
from lexigram.contracts.multimedia.protocols import VideoProcessor
from lexigram.contracts.multimedia.types import MediaAsset, Trim


class _FakeProcessor:
    async def process(self, operation):
        asset = MediaAsset(mime_type="video/mp4", provider="ffmpeg", uri="out.mp4")
        return Ok(asset)


async def test_fake_processor_satisfies_protocol():
    processor: VideoProcessor = _FakeProcessor()
    asset = MediaAsset(mime_type="video/mp4", provider="local-http", uri="a.mp4")
    result: Result[MediaAsset, VideoGenerationError] = await processor.process(
        Trim(asset=asset, start=0.0, end=1.0)
    )
    assert result.is_ok()


def test_isinstance_check_via_runtime_checkable():
    assert isinstance(_FakeProcessor(), VideoProcessor)


def test_process_accepts_progress_callback():
    sig = inspect.signature(VideoProcessor.process)
    param = sig.parameters["progress_callback"]
    assert param.default is None
