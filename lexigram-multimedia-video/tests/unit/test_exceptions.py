from lexigram.contracts.multimedia.exceptions import VideoGenerationError
from lexigram.multimedia.video.exceptions import (
    VideoGenerationAuthenticationError,
    VideoTimeoutError,
)


def test_package_errors_extend_contracts_video_error() -> None:
    assert issubclass(VideoTimeoutError, VideoGenerationError)
    assert issubclass(VideoGenerationAuthenticationError, VideoGenerationError)
