from lexigram.contracts.multimedia.exceptions import TTSError
from lexigram.multimedia.tts.exceptions import (
    TTSAuthenticationError,
    TTSTimeoutError,
)


def test_package_errors_extend_contracts_tts_error() -> None:
    assert issubclass(TTSTimeoutError, TTSError)
    assert issubclass(TTSAuthenticationError, TTSError)
