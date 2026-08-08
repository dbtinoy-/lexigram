import pytest

from shorts_creator.topics import registry

TOPN_SCRIPT = """TITLE: The 5 Stoic Practices That Actually Work
DURATION: 40
WORD COUNT: 100
PACING: 2.5
[HOOK - 3s]
"Most people train the body and neglect the mind."
[BEAT]
[TOP_ITEMS - 33s]
"1. Morning pages before your phone — three pages, no editing."
"2. One voluntary discomfort every day, starting with the cold shower."
"3. Pre-mortem your day: name the one obstacle and your response."
"4. Pause before every reaction and ask what is in your control."
"5. Nightly audit: one win, one lapse, one thing done differently."
[PAUSE]
[CONCLUSION - 4s]
"Train the mind daily, and nothing external can break it."
EMOTIONAL ARC MAP: scattered -> grounded -> unshakable
PHILOSOPHER: Marcus Aurelius
STOIC SOURCE: Marcus Aurelius, Meditations
DAILY PRACTICE: Morning pages before your phone
"""

TOPN_SCRIPT_NO_NUMBERS = """TITLE: Ranked List
DURATION: 40
WORD COUNT: 100
PACING: 2.5
[HOOK - 3s]
"The hook line."
[TOP_ITEMS - Ns]
"1. Item one with a concrete detail."
"2. Item two with a specific action."
"3. Item three with a sensory beat."
"4. Item four with a number in it."
"5. Item five with a clear payoff."
[CONCLUSION - 4s]
"The closing thought."
"""


MYTH_SCRIPT = """TITLE: The 10,000 Hour Myth
DURATION: 41
WORD COUNT: 110
PACING: 2.7
[HOOK - 3s]
"Your mastery countdown is lying to you."
[BEAT]
[CLAIM - 4s]
"You need 10,000 hours to master anything."
[FACT - 7s]
"Deliberate practice beats raw hours in every measured domain."
[FACT - 7s]
"Most elite performers plateau long before 10,000 recorded hours."
[FACT - 7s]
"Feedback quality - not volume - predicts skill in study after study."
[PAUSE]
[TWIST - 8s]
"The myth is the shortcut. The truth is the system."
[CONCLUSION - 4s]
"Mastery is not a count. It is a loop."
EMOTIONAL ARC MAP: curiosity -> doubt -> clarity -> resolve
"""

MYTH_SCRIPT_NO_NUMBERS = """TITLE: Myth Script
DURATION: 40
WORD COUNT: 100
PACING: 2.5
[HOOK - Ns]
"The hook line."
[CLAIM - Ns]
"The belief being debunked."
[FACT - Ns]
"First correcting fact."
[FACT - Ns]
"Second correcting fact."
[FACT - Ns]
"Third correcting fact."
[TWIST - Ns]
"The reframing turn."
[CONCLUSION - Ns]
"The closing line."
"""


@pytest.mark.parametrize("topic_name", ["self_improvement", "stoic", "psychology"])
class TestMythParseBranch:
    def test_myth_structure(self, topic_name):
        script = registry.get(topic_name).parse_script(MYTH_SCRIPT)
        names = [s.name for s in script.sections]
        assert names == ["hook", "claim", "fact", "fact", "fact", "twist", "conclusion"]
        assert script.sections[1].text == "You need 10,000 hours to master anything."
        assert script.sections[5].name == "twist"
        assert script.word_count == 110
        assert script.pacing_wps == 2.7

    def test_myth_saved_form_matches_pipeline_shape(self, topic_name):
        from dataclasses import asdict

        from shorts_creator.pipeline.script_parser import to_pipeline_script

        saved = asdict(registry.get(topic_name).parse_script(MYTH_SCRIPT))
        lines = [s["text"] for s in saved["sections"]]
        pipe = to_pipeline_script(saved)
        assert pipe.claim == "You need 10,000 hours to master anything."
        assert pipe.fact_count == 3
        assert len(pipe.twist) > 0
        assert pipe.message_lines == [
            "You need 10,000 hours to master anything.",
            *lines[2:5],
            "The myth is the shortcut. The truth is the system.",
        ]

    def test_myth_without_header_seconds_backfills(self, topic_name):
        script = registry.get(topic_name).parse_script(MYTH_SCRIPT_NO_NUMBERS)
        names = [s.name for s in script.sections]
        assert names == ["hook", "claim", "fact", "fact", "fact", "twist", "conclusion"]
        assert all(s.duration_seconds > 0 for s in script.sections)
        assert sum(s.duration_seconds for s in script.sections) == pytest.approx(40.0)

    def test_non_myth_text_keeps_native_structure(self, topic_name):
        native = registry.get(topic_name).mock_script()
        parsed = registry.get(topic_name).parse_script(native)
        assert "claim" not in [s.name for s in parsed.sections]
        assert "fact" not in [s.name for s in parsed.sections]
        assert parsed.sections[0].name == "hook"


@pytest.mark.parametrize("topic_name", ["self_improvement", "stoic", "psychology"])
class TestTopNParseBranch:
    def test_topn_structure(self, topic_name):
        script = registry.get(topic_name).parse_script(TOPN_SCRIPT)
        names = [s.name for s in script.sections]
        assert names == [
            "hook",
            "top_items",
            "top_items",
            "top_items",
            "top_items",
            "top_items",
            "conclusion",
        ]
        assert script.total_duration == 40.0
        assert script.word_count == 100
        assert script.pacing_wps == 2.5
        assert script.sections[1].text.startswith("1. ")
        assert script.sections[5].text.startswith("5. ")

    def test_topn_item_durations_split_header_seconds(self, topic_name):
        script = registry.get(topic_name).parse_script(TOPN_SCRIPT)
        item_durs = [s.duration_seconds for s in script.sections if s.name == "top_items"]
        assert sum(item_durs) == pytest.approx(33.0)
        assert len(set(item_durs)) == 1
        assert item_durs[0] == pytest.approx(33.0 / 5)

    def test_topn_without_header_seconds_backfills_items(self, topic_name):
        script = registry.get(topic_name).parse_script(TOPN_SCRIPT_NO_NUMBERS)
        names = [s.name for s in script.sections]
        assert names == [
            "hook",
            "top_items",
            "top_items",
            "top_items",
            "top_items",
            "top_items",
            "conclusion",
        ]
        items_sec = sum(s.duration_seconds for s in script.sections if s.name == "top_items")
        assert items_sec == pytest.approx(33.0)

    def test_non_topn_text_keeps_native_structure(self, topic_name):
        native = registry.get(topic_name).mock_script()
        parsed = registry.get(topic_name).parse_script(native)
        assert parsed.sections[0].name == "hook"
        assert "top_items" not in [s.name for s in parsed.sections]
