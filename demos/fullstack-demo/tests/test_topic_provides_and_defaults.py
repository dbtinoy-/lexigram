import tempfile
from pathlib import Path

import pytest

from shorts_creator.contracts import Severity, TopicSide
from shorts_creator.topics.skill_topic import SkillTopic

GOOD_FRONTMATTER = """\
---
name: mini
label: Mini Topic
description: A minimal test topic
structure_sections: [hook, message_lines]
topic_categories: []
provides:
  script: [hook, message_lines]
  voice: [tts_story]
objectives: [quotable_hook]
default_format: narrated
---

## IDEA_PROMPT
generate {count} ideas
## SCRIPT_PROMPT
write a script of {min_dur}s
"""

NO_CONTRACT_FRONTMATTER = """\
---
name: legacy
label: Legacy Topic
description: Old skill before contract fields
structure_sections: [hook]
topic_categories: []
---

## IDEA_PROMPT
generate {count} ideas
## SCRIPT_PROMPT
write a script of {min_dur}s
"""

BAD_CAPABILITY_FRONTMATTER = """\
---
name: broken
label: Broken Topic
structure_sections: [hook]
topic_categories: []
provides:
  script: [hok]   # typo
  voice: [tts_story]
---

## IDEA_PROMPT
x
## SCRIPT_PROMPT
y
"""


def _write_skill(tmp, content: str, name: str = "mini") -> Path:
    skill_dir = Path(tmp) / name
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "scripts" / "main.py").write_text(
        "from shorts_creator.topics.base import Idea\n"
        "def parse_ideas(text):\n    return []\n"
        "def parse_script(text):\n    from shorts_creator.topics.base import ParsedScript\n    return ParsedScript(title='', sections=[], word_count=0, total_duration=0, emotional_arc='')\n"
        "def mock_ideas(count=3):\n    return ''\n"
        "def mock_script():\n    return ''\n",
        encoding="utf-8",
    )
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


class TestProvidesParsing:
    def test_provides_properties(self):
        with tempfile.TemporaryDirectory() as tmp:
            st = SkillTopic(_write_skill(tmp, GOOD_FRONTMATTER))
            assert st.provides_script == ["hook", "message_lines"]
            assert st.provides_voice == ["tts_story"]
            assert st.objectives == ["quotable_hook"]
            assert st.default_format == "narrated"

    def test_to_contract_side(self):
        with tempfile.TemporaryDirectory() as tmp:
            side = SkillTopic(_write_skill(tmp, GOOD_FRONTMATTER)).to_contract_side()
        assert isinstance(side, TopicSide)
        assert side.script == frozenset({"hook", "message_lines"})
        assert side.voice == frozenset({"tts_story"})
        assert side.objectives == frozenset({"quotable_hook"})

    def test_absent_fields_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            st = SkillTopic(_write_skill(tmp, NO_CONTRACT_FRONTMATTER, name="legacy"))
            assert st.provides_script == []
            assert st.provides_voice == []
            assert st.objectives == []
            assert st.default_format is None

    def test_typo_in_provides_raises(self):
        with tempfile.TemporaryDirectory() as tmp, pytest.raises(Exception) as excinfo:
            SkillTopic(_write_skill(tmp, BAD_CAPABILITY_FRONTMATTER, name="broken"))
        assert "hok" in str(excinfo.value)

    def test_never_rewrites_skill_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_skill(tmp, GOOD_FRONTMATTER)
            before = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            st = SkillTopic(skill_dir)
            _ = st.to_contract_side()
            assert (skill_dir / "SKILL.md").read_text(encoding="utf-8") == before


class TestRealSkillsContract:
    def test_real_skills_load_with_provides(self):
        from shorts_creator.topics import registry

        for topic in registry.available:
            side = topic.to_contract_side() if hasattr(topic, "to_contract_side") else None
            if side is None:
                continue
            assert "hook" in side.script
            assert "tts_story" in side.voice

    def test_real_skills_all_compatible_with_narrated(self):
        from shorts_creator.contracts.matcher import validate_pair
        from shorts_creator.formats import registry as formats
        from shorts_creator.topics import registry

        fmt = formats.get("narrated")
        assert fmt is not None
        side = fmt.to_contract_side()
        for topic in registry.available:
            topic_side = topic.to_contract_side()
            assert not any(i.severity is Severity.ERROR for i in validate_pair(topic_side, side)), (
                f"{topic.name} ×.narrated.should be valid"
            )
