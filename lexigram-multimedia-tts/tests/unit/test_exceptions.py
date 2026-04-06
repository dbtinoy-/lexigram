from lexigram.contracts.multimedia.exceptions import TTSError
from lexigram.multimedia.tts.exceptions import TTSAuthenticationError


def test_package_errors_extend_contracts_tts_error() -> None:
    assert issubclass(TTSAuthenticationError, TTSError)
