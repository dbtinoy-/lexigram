import importlib
from pathlib import Path

from shorts_creator.topics import registry
from shorts_creator.topics.skill_topic import SkillTopic

_SKILLS_DIR = Path(__file__).resolve().parent.parent / "data" / "skills"


def test_banned_phrases_accessor():
    st = registry.get("self_improvement")
    assert st is not None
    phrases = st.banned_phrases
    assert isinstance(phrases, list)
    assert len(phrases) > 0
    assert all(isinstance(p, str) for p in phrases)


def test_structured_builtin_values_are_exposed():
    st = registry.get("self_improvement")
    assert st is not None
    assert st.label
    assert st.description
    assert isinstance(st.structure_sections, list)
    assert isinstance(st.topic_categories, list)
    assert st.idea_prompt
    assert st.script_prompt


def test_no_frontmatter_write_hook_is_exposed():
    module = importlib.import_module("shorts_creator.topics.skill_topic")
    assert not hasattr(module, "_write_skill_md_frontmatter")


def test_reading_a_skill_never_rewrites_the_prompt_file():
    skill_dir = _SKILLS_DIR / "self_improvement"
    md_path = skill_dir / "SKILL.md"
    before = md_path.read_text(encoding="utf-8")

    st = SkillTopic(skill_dir)
    _ = st.idea_prompt
    _ = st.script_prompt
    _ = st.banned_phrases

    assert md_path.read_text(encoding="utf-8") == before


def test_discovered_types_have_banned_phrases():
    for st in registry.available:
        assert isinstance(st.banned_phrases, list)


def test_background_queries_accessor():
    st = registry.get("self_improvement")
    assert st is not None
    queries = st.background_queries
    assert isinstance(queries, list)
    assert len(queries) > 0
    assert all(isinstance(q, str) for q in queries)


def test_all_topics_expose_background_queries():
    for st in registry.available:
        assert isinstance(st.background_queries, list)


def test_parse_skill_md_reads_background_queries(tmp_path):
    md = tmp_path / "SKILL.md"
    md.write_text(
        "---\nname: test_topic\nlabel: Test\ndescription: d\n"
        "structure_sections: [hook]\nprovides: {script: [hook]}\n"
        "background_queries: [morning run, mountain summit]\n---\nbody\n",
        encoding="utf-8",
    )
    from shorts_creator.topics.skill_topic import _parse_skill_md

    assert _parse_skill_md(md)["background_queries"] == ["morning run", "mountain summit"]


def test_parse_skill_md_missing_background_queries_defaults_empty(tmp_path):
    md = tmp_path / "SKILL.md"
    md.write_text(
        "---\nname: test_topic\nlabel: Test\ndescription: d\n"
        "structure_sections: [hook]\nprovides: {script: [hook]}\n---\nbody\n",
        encoding="utf-8",
    )
    from shorts_creator.topics.skill_topic import _parse_skill_md

    assert _parse_skill_md(md)["background_queries"] == []
