import pytest

from shorts_creator.contracts.capabilities import (
    CapabilityVocabularyError,
    parse_capabilities,
)


class TestParseCapabilities:
    def test_parses_known_script_names(self):
        assert parse_capabilities(["hook", "problem"], "script") == ["hook", "problem"]

    def test_parses_known_voice_names(self):
        assert parse_capabilities(["tts_story"], "voice") == ["tts_story"]

    def test_parses_known_pipeline_names(self):
        names = parse_capabilities(["captions", "background", "tts_story"], "pipeline")
        assert names == ["captions", "background", "tts_story"]

    def test_unknown_name_raises_with_valid_list(self):
        with pytest.raises(CapabilityVocabularyError) as excinfo:
            parse_capabilities(["hook", "bogus_cap"], "script")
        assert excinfo.value.kind == "script"
        assert excinfo.value.name == "bogus_cap"
        assert "hook" in excinfo.value.valid

    def test_whitespace_normalized(self):
        assert parse_capabilities([" hook ", "problem"], "script") == ["hook", "problem"]

    def test_typo_rejected(self):
        with pytest.raises(CapabilityVocabularyError):
            parse_capabilities(["hok"], "script")

    def test_deduplicates(self):
        assert parse_capabilities(["hook", "hook", "problem"], "script") == ["hook", "problem"]

    def test_empty_and_none(self):
        assert parse_capabilities(None, "script") == []
        assert parse_capabilities([], "script") == []

    def test_unknown_kind_raises(self):
        with pytest.raises(KeyError):
            parse_capabilities(["hook"], "nonsense")


def test_narrated_requires_music_beat():
    from shorts_creator.formats import registry

    fmt = registry.get("narrated")
    assert "music_beat" in (fmt.requires.get("pipeline") or [])
