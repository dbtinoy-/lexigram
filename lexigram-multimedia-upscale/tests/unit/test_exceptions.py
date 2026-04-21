from lexigram.contracts.multimedia.exceptions import UpscaleError
from lexigram.multimedia.upscale.exceptions import UpscaleTimeoutError


def test_upscale_timeout_error_extends_upscale_error() -> None:
    assert issubclass(UpscaleTimeoutError, UpscaleError)
    assert UpscaleTimeoutError._code == "LEX_ERR_MM_UPSCALE_001"
