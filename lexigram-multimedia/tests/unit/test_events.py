from lexigram.contracts.domain.events import DomainEvent
from lexigram.multimedia.events import MultimediaGenerationEvent


def test_event_extends_domain_event() -> None:
    assert issubclass(MultimediaGenerationEvent, DomainEvent)


def test_event_carries_provider_and_media_type() -> None:
    event = MultimediaGenerationEvent(
        media_type="tts", provider="elevenlabs", size_bytes=1024, duration_seconds=None
    )
    assert event.media_type == "tts"
    assert event.provider == "elevenlabs"
