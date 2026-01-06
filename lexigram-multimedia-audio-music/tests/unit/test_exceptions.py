from lexigram.contracts.multimedia.exceptions import MusicGenerationError
from lexigram.multimedia.audio_music.exceptions import (
    MusicGenerationAuthenticationError,
    MusicTimeoutError,
)


def test_package_errors_extend_contracts_music_error() -> None:
    assert issubclass(MusicTimeoutError, MusicGenerationError)
    assert issubclass(MusicGenerationAuthenticationError, MusicGenerationError)
