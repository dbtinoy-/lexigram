import pytest

from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.multimedia.audio_music.providers.stability_audio import (
    StabilityAudioMusicProvider,
)


def test_stability_stub_raises_not_installed() -> None:
    with pytest.raises(ProviderNotInstalledError):
        StabilityAudioMusicProvider()
