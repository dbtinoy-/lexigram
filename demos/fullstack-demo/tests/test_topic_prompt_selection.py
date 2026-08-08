from shorts_creator.formats import registry as format_registry
from shorts_creator.topics import registry
from shorts_creator.topics.base import Idea

IDEAS = [
    (registry.get("self_improvement"), "[MESSAGE - Ns]"),
    (registry.get("stoic"), "[PRINCIPLE - Ns]"),
    (registry.get("psychology"), "[EXPLANATION - Ns]"),
]


def _idea() -> Idea:
    return Idea(
        title="The 5 Stoic Practices That Actually Work",
        core_message="Five concrete practices that build resilience.",
        hook_line="Most people meditate wrong.",
        identity_signal="You are disciplined.",
        permission_given="It is okay to start small.",
        emotional_arc="Frustrated -> Grounded",
        target_audience="Overwhelmed professionals",
        quotability_score=9.0,
        share_trigger="It reframes a habit they already have.",
    )


class TestTopNPromptSelection:
    def test_topn_selects_topn_body(self):
        for topic, _ in IDEAS:
            prompt = topic.build_script_prompt(_idea(), format_name="topn")
            assert "[TOP_ITEMS - Ns]" in prompt
            assert '"1. [Item 1]"' in prompt
            assert '"5. [Item 5]"' in prompt

    def test_default_format_selects_default_body(self):
        for topic, marker in IDEAS:
            prompt = topic.build_script_prompt(_idea(), format_name="narrated")
            assert marker in prompt
            assert "[TOP_ITEMS - Ns]" not in prompt

    def test_placeholders_filled_no_leftover_braces(self):
        for topic, _ in IDEAS:
            prompt = topic.build_script_prompt(_idea(), format_name="topn")
            assert "The 5 Stoic Practices That Actually Work" in prompt
            assert "Frustrated -> Grounded" in prompt
            assert "{" not in prompt.replace("target_audience}", "")

    def test_unknown_format_defaults_to_default_body(self):
        prompt = IDEAS[0][0].build_script_prompt(_idea(), format_name="no_such_format")
        assert "[MESSAGE - Ns]" in prompt
        assert "[TOP_ITEMS - Ns]" not in prompt


class TestMythPromptSelection:
    def test_myth_selects_myth_body(self):
        for topic, _ in IDEAS:
            prompt = topic.build_script_prompt(_idea(), format_name="myth")
            assert "[CLAIM - Ns]" in prompt
            assert "[FACT - Ns]" in prompt
            assert "[TWIST - Ns]" in prompt

    def test_myth_does_not_leak_other_bodies(self):
        for topic, _ in IDEAS:
            prompt = topic.build_script_prompt(_idea(), format_name="myth")
            assert "[TOP_ITEMS - Ns]" not in prompt
            assert "[MESSAGE - Ns]" not in prompt
            assert "[EXPLANATION - Ns]" not in prompt
            assert "[PRINCIPLE - Ns]" not in prompt

    def test_myth_placeholders_filled_no_leftover_braces(self):
        for topic, _ in IDEAS:
            prompt = topic.build_script_prompt(_idea(), format_name="myth")
            assert "The 5 Stoic Practices That Actually Work" in prompt
            assert "Frustrated -> Grounded" in prompt
            assert "{" not in prompt.replace("target_audience}", "")

    def test_narrated_and_topn_do_not_use_myth_body(self):
        for topic, _ in IDEAS:
            narrated = topic.build_script_prompt(_idea(), format_name="narrated")
            topn = topic.build_script_prompt(_idea(), format_name="topn")
            assert "[CLAIM - Ns]" not in narrated
            assert "[CLAIM - Ns]" not in topn


class TestVoiceProfile:
    def test_script_prompt_contains_voice_block_when_given(self):
        voice = {
            "audience_persona": "busy founders",
            "tone_rules": ["no jargon", "short sentences"],
            "banned_topics": ["politics"],
        }
        for topic, _ in IDEAS:
            prompt = topic.build_script_prompt(_idea(), format_name="narrated", voice=voice)
            assert "VOICE PROFILE:" in prompt
            assert "- Audience persona: busy founders" in prompt
            assert "- Tone rules: no jargon; short sentences" in prompt
            assert "- Never mention: politics" in prompt
            assert "Follow this voice profile throughout." in prompt

    def test_script_prompt_voice_absent_when_none(self):
        for topic, _ in IDEAS:
            prompt = topic.build_script_prompt(_idea(), format_name="narrated")
            assert "VOICE PROFILE" not in prompt

    def test_script_prompt_partial_voice_skips_empty_parts(self):
        prompt = IDEAS[0][0].build_script_prompt(
            _idea(), format_name="narrated", voice={"audience_persona": "founders"}
        )
        assert "- Audience persona: founders" in prompt
        assert "Tone rules" not in prompt
        assert "Never mention" not in prompt

    def test_idea_prompt_contains_voice_block_when_given(self):
        voice = {"audience_persona": "busy founders", "banned_topics": ["politics"]}
        prompt = IDEAS[0][0].build_idea_prompt(count=5, focus="habits", voice=voice)
        assert "VOICE PROFILE:" in prompt
        assert "- Audience persona: busy founders" in prompt
        assert "- Never mention: politics" in prompt
        assert "Follow this voice profile throughout." in prompt

    def test_idea_prompt_voice_absent_when_none(self):
        prompt = IDEAS[0][0].build_idea_prompt(count=5, focus="habits")
        assert "VOICE PROFILE" not in prompt


class TestPacingTarget:
    def test_pacing_target_appears_when_given(self):
        for topic, _ in IDEAS:
            prompt = topic.build_script_prompt(_idea(), format_name="narrated", pacing_wps=2.5)
            assert "TARGET PACING: 2.5 words per second" in prompt

    def test_pacing_target_absent_when_none(self):
        prompt = IDEAS[0][0].build_script_prompt(_idea(), format_name="narrated")
        assert "TARGET PACING" not in prompt

    def test_pacing_word_budget_matches_target(self):
        fmt = format_registry.get("narrated")
        sweet = (fmt.duration_range[0] + fmt.duration_range[1]) // 2
        expected = int(sweet * 2.5)
        prompt = IDEAS[0][0].build_script_prompt(_idea(), format_name="narrated", pacing_wps=2.5)
        assert str(expected) in prompt
        assert prompt.count(str(expected)) >= 2

    def test_pacing_clamps_to_format_range(self):
        fmt = format_registry.get("narrated")
        lo, hi = fmt.pacing_wps_range
        topic = IDEAS[0][0]
        prompt = topic.build_script_prompt(_idea(), format_name="narrated", pacing_wps=99.0)
        assert "TARGET PACING: 99.0" not in prompt
        assert f"TARGET PACING: {hi:.1f}" in prompt
        prompt_low = topic.build_script_prompt(_idea(), format_name="narrated", pacing_wps=0.01)
        assert "TARGET PACING: 0.0" not in prompt_low
        assert f"TARGET PACING: {lo:.1f}" in prompt_low
