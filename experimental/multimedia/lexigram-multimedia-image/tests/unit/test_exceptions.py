from lexigram.contracts.multimedia.exceptions import ImageGenerationError
from lexigram.multimedia.image.exceptions import (
    ImageGenerationAuthenticationError,
    ImageTimeoutError,
)


def test_package_errors_extend_contracts_image_error() -> None:
    assert issubclass(ImageTimeoutError, ImageGenerationError)
    assert issubclass(ImageGenerationAuthenticationError, ImageGenerationError)


def test_error_codes_are_dedicated_not_inherited() -> None:
    assert ImageTimeoutError().code == "LEX_ERR_MM_IMAGE_001"
    assert ImageGenerationAuthenticationError().code == "LEX_ERR_MM_IMAGE_002"
