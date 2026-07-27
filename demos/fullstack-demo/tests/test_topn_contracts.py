from shorts_creator.contracts import (
    FUTURE_PIPELINE_CAPABILITIES,
    PIPELINE_CAPABILITIES,
)
from shorts_creator.contracts.capabilities import parse_capabilities


class TestTopNContractVocabulary:
    def test_script_top_items_parses(self):
        assert parse_capabilities(["hook", "top_items", "conclusion"], "script") == [
            "hook",
            "top_items",
            "conclusion",
        ]

    def test_pipeline_music_beat_parses(self):
        assert parse_capabilities(["music_beat", "tts_story"], "pipeline") == [
            "music_beat",
            "tts_story",
        ]

    def test_pipeline_music_beat_is_implemented(self):
        assert "music_beat" in PIPELINE_CAPABILITIES
        assert "analyze" in PIPELINE_CAPABILITIES["music_beat"]
        assert "bake" in PIPELINE_CAPABILITIES["music_beat"]

    def test_pipeline_music_beat_not_future(self):
        assert "music_beat" not in FUTURE_PIPELINE_CAPABILITIES
