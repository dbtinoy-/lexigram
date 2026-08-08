from shorts_creator.pipeline.script_parser import (
    apply_profile_overrides,
    parse_script,
    to_pipeline_script,
)


class TestApplyProfileOverrides:
    def test_hook_text_overrides_sections_format_hook(self):
        saved = {
            "title": "T",
            "sections": [
                {"name": "hook", "text": "Original hook", "duration_seconds": 4.0},
                {"name": "message", "text": "M", "duration_seconds": 6.0},
            ],
        }
        script = apply_profile_overrides(saved, {"hook_text": "New hook"})
        assert script.hook == "New hook"
        assert script.message_lines == ["M"]

    def test_hook_text_overrides_legacy_top_level_hook(self):
        saved = {
            "title": "T",
            "duration_seconds": 10.0,
            "hook": "Original hook",
            "hook_seconds": 4.0,
            "message_lines": ["M"],
            "message_seconds": 6.0,
        }
        script = apply_profile_overrides(saved, {"hook_text": "New hook"})
        assert script.hook == "New hook"

    def test_section_texts_replace_only_matching_sections(self):
        saved = {
            "title": "T",
            "sections": [
                {"name": "hook", "text": "H", "duration_seconds": 4.0},
                {"name": "message", "text": "Original message", "duration_seconds": 6.0},
                {"name": "conclusion", "text": "C", "duration_seconds": 2.0},
            ],
        }
        script = apply_profile_overrides(saved, {"section_texts": {"message": "New message"}})
        assert script.message_lines == ["New message"]
        assert script.hook == "H"
        assert script.conclusion == "C"

    def test_section_texts_keeps_duplicate_top_items_intact(self):
        saved = {
            "title": "T",
            "sections": [
                {"name": "hook", "text": "H", "duration_seconds": 3.0},
                {"name": "top_items", "text": "1. First", "duration_seconds": 6.6},
                {"name": "top_items", "text": "2. Second", "duration_seconds": 6.6},
                {"name": "conclusion", "text": "C", "duration_seconds": 4.0},
            ],
        }
        script = apply_profile_overrides(saved, {"section_texts": {"top_items": "Overridden"}})
        assert script.top_items == ["Overridden", "Overridden"]
        assert script.top_items_seconds == 13.2

    def test_empty_snapshot_identical_to_to_pipeline_script(self):
        saved = {
            "title": "T",
            "sections": [
                {"name": "hook", "text": "H", "duration_seconds": 4.0},
                {"name": "message", "text": "M", "duration_seconds": 6.0},
            ],
        }
        assert apply_profile_overrides(saved, None) == to_pipeline_script(saved)
        assert apply_profile_overrides(saved, {}) == to_pipeline_script(saved)

    def test_hook_text_does_not_replace_when_empty(self):
        saved = {
            "title": "T",
            "sections": [{"name": "hook", "text": "Keep me", "duration_seconds": 4.0}],
        }
        script = apply_profile_overrides(saved, {"hook_text": "  "})
        assert script.hook == "Keep me"


class TestToPipelineScript:
    def test_psychology_sections_fold_middle_sections_into_message(self):
        saved = {
            "title": "Why We Procrastinate",
            "sections": [
                {"name": "hook", "text": "Hook", "duration_seconds": 4.0},
                {"name": "context", "text": "Context", "duration_seconds": 8.0},
                {"name": "explanation", "text": "Explanation", "duration_seconds": 10.0},
                {"name": "application", "text": "Application", "duration_seconds": 8.0},
                {"name": "reflection", "text": "Reflection", "duration_seconds": 5.0},
            ],
        }
        s = to_pipeline_script(saved)
        assert s.hook == "Hook"
        assert s.message_lines == ["Context", "Explanation", "Application", "Reflection"]
        assert s.message_seconds == 31.0
        assert s.metaphor == ""
        assert s.conclusion == ""

    def test_legacy_top_level_format(self):
        saved = {
            "title": "Legacy",
            "duration_seconds": 35.0,
            "word_count": 140,
            "pacing_wps": 4.0,
            "hook": "Legacy hook",
            "hook_seconds": 6.0,
            "message_lines": ["Line 1", "Line 2"],
            "message_seconds": 15.0,
            "metaphor": "Legacy metaphor",
            "metaphor_seconds": 5.0,
            "conclusion": "Legacy conclusion",
            "conclusion_seconds": 4.0,
            "emotional_arc": ["a", "b"],
            "parallel_structure": "parallel",
            "hook_score": "8/10",
        }
        s = to_pipeline_script(saved)
        assert s.duration_seconds == 35.0
        assert s.hook == "Legacy hook"
        assert s.message_lines == ["Line 1", "Line 2"]
        assert s.metaphor == "Legacy metaphor"
        assert s.parallel_structure == "parallel"
        assert s.hook_score == "8/10"

    def test_missing_duration_falls_back_to_section_sum(self):
        saved = {
            "title": "No Total",
            "sections": [
                {"name": "hook", "text": "H", "duration_seconds": 4.0},
                {"name": "message", "text": "M", "duration_seconds": 6.0},
            ],
        }
        s = to_pipeline_script(saved)
        assert s.duration_seconds == 10.0

    def test_legacy_cta_section_folds_into_message_lines(self):
        saved = {
            "title": "T",
            "duration_seconds": 10.0,
            "word_count": 20,
            "pacing_wps": 2.0,
            "sections": [
                {"name": "hook", "text": "H", "duration_seconds": 1.0},
                {"name": "message", "text": "M", "duration_seconds": 3.0},
                {"name": "conclusion", "text": "C", "duration_seconds": 2.0},
                {"name": "cta", "text": "Subscribe", "duration_seconds": 4.0},
            ],
        }
        s = to_pipeline_script(saved)
        assert not hasattr(s, "cta")
        assert s.message_lines == ["M", "Subscribe"]
        assert s.conclusion == "C"

    def test_parsed_script_has_no_cta_field(self):
        script = parse_script("""TITLE: T
DURATION: 6
WORD COUNT: 10
PACING: 1.7
[HOOK - 1s]
"H"
[MESSAGE - 3s]
"Line one"
[METAPHOR - 1s]
"Met"
[CONCLUSION - 1s]
"End"
EMOTIONAL ARC MAP: a -> b
PARALLEL STRUCTURE USED: P
HOOK SCORE: 8""")
        assert not hasattr(script, "cta")
        assert not hasattr(script, "cta_seconds")
        assert script.hook == "H"
        assert script.conclusion == "End"
        assert script.duration_seconds == 6.0


class TestTopItems:
    def test_to_pipeline_script_extracts_top_items_not_folded(self):
        saved = {
            "title": "Ranked",
            "total_duration": 40.0,
            "sections": [
                {"name": "hook", "text": "H", "duration_seconds": 3.0},
                {"name": "top_items", "text": "1. First", "duration_seconds": 6.6},
                {"name": "top_items", "text": "2. Second", "duration_seconds": 6.6},
                {"name": "top_items", "text": "3. Third", "duration_seconds": 6.6},
                {"name": "top_items", "text": "4. Fourth", "duration_seconds": 6.6},
                {"name": "top_items", "text": "5. Fifth", "duration_seconds": 6.6},
                {"name": "conclusion", "text": "C", "duration_seconds": 4.0},
            ],
        }
        s = to_pipeline_script(saved)
        assert s.top_items == ["1. First", "2. Second", "3. Third", "4. Fourth", "5. Fifth"]
        assert s.top_items_seconds == 33.0
        assert s.message_lines == []
        assert s.message_seconds == 0.0
        assert s.duration_seconds == 40.0

    def test_legacy_top_level_top_items_keys(self):
        saved = {
            "title": "Legacy Ranked",
            "duration_seconds": 20.0,
            "hook": "H",
            "top_items": ["1. A", "2. B"],
            "top_items_seconds": 12.0,
            "message_lines": [],
        }
        s = to_pipeline_script(saved)
        assert s.top_items == ["1. A", "2. B"]
        assert s.top_items_seconds == 12.0

    def test_raw_parse_script_handles_top_items_block(self):
        script = parse_script("""TITLE: T
DURATION: 20
WORD COUNT: 50
PACING: 2.5
[HOOK - 3s]
"H"
[TOP_ITEMS - 13s]
"1. One"
"2. Two"
"3. Three"
"4. Four"
"5. Five"
[METAPHOR - 1s]
"Met"
[CONCLUSION - 4s]
"End"
EMOTIONAL ARC MAP: a -> b""")
        assert script.top_items == ["1. One", "2. Two", "3. Three", "4. Four", "5. Five"]
        assert script.top_items_seconds == 13.0
        assert script.duration_seconds == 20.0
        assert script.message_lines == []

    def test_raw_parse_script_top_items_placeholder_backfilled(self):
        script = parse_script("""TITLE: T
DURATION: 20
WORD COUNT: 50
PACING: 2.5
[HOOK - 3s]
"H"
[TOP_ITEMS - Ns]
"1. One"
"2. Two"
"3. Three"
"4. Four"
"5. Five"
[MESSAGE - 2s]
"Bridge"
[METAPHOR - 1s]
"Met"
[CONCLUSION - 4s]
"End"
EMOTIONAL ARC MAP: a -> b""")
        assert script.top_items_seconds == 10.0
        assert script.duration_seconds == 20.0
