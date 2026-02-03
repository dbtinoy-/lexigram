from lexigram.contracts.multimedia.exceptions import MultimediaError
from lexigram.multimedia.interpolate.exceptions import InterpolationTimeoutError


def test_interpolation_timeout_error_extends_multimedia_error() -> None:
    assert issubclass(InterpolationTimeoutError, MultimediaError)
    assert InterpolationTimeoutError._code == "LEX_ERR_MM_INTERPOLATE_001"
