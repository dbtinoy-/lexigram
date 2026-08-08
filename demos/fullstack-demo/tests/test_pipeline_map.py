from shorts_creator.contracts import (
    FUTURE_PIPELINE_CAPABILITIES,
    PIPELINE_CAPABILITIES,
)
from shorts_creator.contracts.pipeline import PIPELINE_CAPABILITIES as _P


class TestPipelineMap:
    def test_expected_keys_are_all_implemented(self):
        assert set(_P) == {
            "word_timing",
            "captions",
            "background",
            "outro",
            "tts_story",
            "music_beat",
            "ranked_screens",
        }

    def test_values_point_at_stages(self):
        assert "align_words" in _P["word_timing"]
        assert "synthesize_batch" in _P["tts_story"]
        assert "chunk" in _P["captions"]
        assert "stock_video" in _P["background"]
        assert "outro" in _P["outro"]
        assert "music_beat" in _P["music_beat"]
        assert "ranked_clip" in _P["ranked_screens"]

    def test_future_set_does_not_overlap_implemented(self):
        assert FUTURE_PIPELINE_CAPABILITIES.isdisjoint(set(_P))

    def test_future_capabilities_known(self):
        assert FUTURE_PIPELINE_CAPABILITIES == frozenset({"silent_frames", "screen_tutorial"})

    def test_public_re_exports_match(self):
        assert PIPELINE_CAPABILITIES is _P
        assert FUTURE_PIPELINE_CAPABILITIES is not None
