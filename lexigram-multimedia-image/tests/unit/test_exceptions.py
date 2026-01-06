from lexigram.contracts.multimedia.exceptions import ImageGenerationError
from lexigram.multimedia.image.exceptions import (
    ImageGenerationAuthenticationError,
    ImageTimeoutError,
)


def test_package_errors_extend_contracts_image_error() -> None:
    assert issubclass(ImageTimeoutError, ImageGenerationError)
    assert issubclass(ImageGenerationAuthenticationError, ImageGenerationError)
