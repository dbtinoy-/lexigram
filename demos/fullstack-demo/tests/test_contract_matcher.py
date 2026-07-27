from shorts_creator.contracts import (
    FormatSide,
    Severity,
    TopicSide,
    incompatible_reasons,
    is_valid_pair,
    validate_pair,
)

_STOIC = TopicSide(
    script=frozenset({"hook", "problem", "principle", "practice", "reflection"}),
    voice=frozenset({"tts_story"}),
    objectives=frozenset(),
)

_NARRATION = FormatSide(
    name="narrated",
    requires_script=frozenset({"hook"}),
    requires_voice=frozenset({"tts_story"}),
    requires_pipeline=frozenset({"tts_story", "word_timing", "captions", "background", "outro"}),
    requires_assets=frozenset(),
    objectives=frozenset(),
)


class TestValidPair:
    def test_stoic_x_narrated_is_valid(self):
        assert is_valid_pair(_STOIC, _NARRATION)
        assert validate_pair(_STOIC, _NARRATION) == []


class TestFailCases:
    def test_req_script_when_topic_lacks_capability(self):
        listicle = FormatSide(
            name="listicle",
            requires_script=frozenset({"hook", "message_lines"}),
            requires_voice=frozenset({"tts_story"}),
            requires_pipeline=frozenset({"captions"}),
            requires_assets=frozenset(),
            objectives=frozenset(),
        )
        issues = validate_pair(_STOIC, listicle)
        fails = [i for i in issues if i.severity is Severity.ERROR]
        assert [i.code for i in fails] == ["REQ_SCRIPT"]
        assert "message_lines" in fails[0].message

    def test_req_voice_when_topic_cannot_speak(self):
        silent = FormatSide(
            name="silent",
            requires_script=frozenset({"hook"}),
            requires_voice=frozenset({"voice_over"}),
            requires_pipeline=frozenset({"captions"}),
            requires_assets=frozenset(),
            objectives=frozenset(),
        )
        fails = [i for i in validate_pair(_STOIC, silent) if i.severity is Severity.ERROR]
        assert [i.code for i in fails] == ["REQ_VOICE"]

    def test_req_pipeline_when_stage_unimplemented(self):
        beat_synced = FormatSide(
            name="beat_synced",
            requires_script=frozenset({"hook"}),
            requires_voice=frozenset({"tts_story"}),
            requires_pipeline=frozenset({"silent_frames"}),  # future, unimplemented
            requires_assets=frozenset(),
            objectives=frozenset(),
        )
        fails = [i for i in validate_pair(_STOIC, beat_synced) if i.severity is Severity.ERROR]
        assert [i.code for i in fails] == ["REQ_PIPELINE"]
        assert "silent_frames" in fails[0].message


class TestWarnCases:
    def test_objective_not_supported_warns_only(self):
        objective_fmt = FormatSide(
            name="narrated",
            requires_script=frozenset({"hook"}),
            requires_voice=frozenset({"tts_story"}),
            requires_pipeline=frozenset({"captions"}),
            requires_assets=frozenset(),
            objectives=frozenset({"quotable_hook"}),
        )
        issues = validate_pair(_STOIC, objective_fmt)
        assert is_valid_pair(_STOIC, objective_fmt)
        assert [i.code for i in issues] == ["OBJ_NOT_SUPPORTED"]

    def test_supported_objective_no_warn(self):
        objective_fmt = FormatSide(
            name="narrated",
            requires_script=frozenset({"hook"}),
            requires_voice=frozenset({"tts_story"}),
            requires_pipeline=frozenset({"captions"}),
            requires_assets=frozenset(),
            objectives=frozenset({"quotable_hook"}),
        )
        quotable_topic = TopicSide(
            script=frozenset({"hook"}),
            voice=frozenset({"tts_story"}),
            objectives=frozenset({"quotable_hook"}),
        )
        assert validate_pair(quotable_topic, objective_fmt) == []


class TestHelperViews:
    def test_incompatible_reasons_only_fail_severity(self):
        bad = FormatSide(
            name="bad",
            requires_script=frozenset({"message_lines"}),
            requires_voice=frozenset({"tts_story"}),
            requires_pipeline=frozenset({"silent_frames"}),
            requires_assets=frozenset(),
            objectives=frozenset(),
        )
        reasons = incompatible_reasons(_STOIC, bad)
        assert any("message_lines" in r for r in reasons)
        assert any("silent_frames" in r for r in reasons)

    def test_valid_pair_no_reasons(self):
        assert incompatible_reasons(_STOIC, _NARRATION) == []
