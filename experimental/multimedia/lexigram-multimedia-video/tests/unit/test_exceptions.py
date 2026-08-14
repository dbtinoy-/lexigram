from lexigram.contracts.multimedia.exceptions import VideoGenerationError
from lexigram.multimedia.video.exceptions import (
    VideoGenerationAuthenticationError,
    VideoProcessingError,
    VideoTimeoutError,
)


def test_package_errors_extend_contracts_video_error() -> None:
    assert issubclass(VideoTimeoutError, VideoGenerationError)
    assert issubclass(VideoGenerationAuthenticationError, VideoGenerationError)
    assert issubclass(VideoProcessingError, VideoGenerationError)


def test_video_processing_error_code() -> None:
    assert VideoProcessingError("boom").code == "LEX_ERR_MM_VIDEO_003"
