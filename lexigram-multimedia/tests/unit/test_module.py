from lexigram.contracts.multimedia.protocols import (
    BeatAnalysisProvider,
    ImageProvider,
    InterpolationProvider,
    MusicProvider,
    TTSProvider,
    UpscaleProvider,
    VideoProvider,
)
from lexigram.multimedia.di.provider import MultimediaProvider
from lexigram.multimedia.module import MultimediaModule


def test_configure_builds_dynamic_module_with_provider_and_exports() -> None:
    module = MultimediaModule.configure()

    assert module.module is MultimediaModule
    assert len(module.providers) == 1
    assert isinstance(module.providers[0], MultimediaProvider)
    assert set(module.exports) == {
        TTSProvider,
        MusicProvider,
        VideoProvider,
        ImageProvider,
        UpscaleProvider,
        InterpolationProvider,
        BeatAnalysisProvider,
    }


def test_configure_accepts_custom_config() -> None:
    from lexigram.multimedia.config import MultimediaConfig

    config = MultimediaConfig()
    module = MultimediaModule.configure(config)

    assert module.providers[0]._multimedia_config is config


def test_stub_returns_dynamic_module_with_exports() -> None:
    module = MultimediaModule.stub()

    assert module.module is MultimediaModule
    assert set(module.exports) == {
        TTSProvider,
        MusicProvider,
        VideoProvider,
        ImageProvider,
        UpscaleProvider,
        InterpolationProvider,
        BeatAnalysisProvider,
    }


def test_stub_tolerates_failing_entry_point_loads() -> None:
    from unittest.mock import MagicMock, patch

    broken_ep = MagicMock()
    broken_ep.load.side_effect = ImportError("broken")
    good_ep = MagicMock()
    good_ep.load.side_effect = AttributeError("no stub")

    with patch(
        "importlib.metadata.entry_points",
        return_value=[broken_ep, good_ep],
    ):
        module = MultimediaModule.stub()

    assert module.module is MultimediaModule
    assert module.imports == []
