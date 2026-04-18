from lexigram.contracts.exceptions.domain import DomainError
from lexigram.contracts.multimedia.exceptions import (
    ImageGenerationError,
    MultimediaError,
    MusicGenerationError,
    ProviderNotInstalledError,
    TTSError,
    VideoGenerationError,
)


def test_multimedia_error_extends_domain_error() -> None:
    assert issubclass(MultimediaError, DomainError)


def test_media_type_errors_extend_multimedia_error() -> None:
    for exc_cls in (TTSError, MusicGenerationError, VideoGenerationError, ImageGenerationError):
        assert issubclass(exc_cls, MultimediaError)


def test_provider_not_installed_error_has_actionable_message() -> None:
    err = ProviderNotInstalledError(
        "pip install lexigram-multimedia-tts[elevenlabs]"
    )
    assert "pip install" in err.message
