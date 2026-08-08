"""Tests for TopicRegistry."""

from shorts_creator.topics import registry


class TestTopicRegistry:
    def test_singleton_has_types(self):
        assert len(registry.names()) >= 2

    def test_build_pipeline(self):
        result = registry.build_pipeline("self_improvement", ["generate", "parse"])
        assert result is not None
        assert result["name"] == "self_improvement_pipeline"
        assert result["steps"] == ["generate", "parse"]

    def test_build_pipeline_unknown(self):
        assert registry.build_pipeline("nonexistent", []) is None

    def test_choices(self):
        choices = registry.choices()
        assert len(choices) >= 2
        si = next(c for c in choices if c["name"] == "self_improvement")
        assert "Self-Improvement" in si["label"]
        psy = next(c for c in choices if c["name"] == "psychology")
        assert "Psychology" in psy["label"]

    def test_skills_available(self):
        skills = registry.skills
        assert len(skills) >= 2
        names = {s.name for s in skills}
        assert "topic_self_improvement" in names
        assert "topic_psychology" in names

    def test_get_skill(self):
        si = registry.get_skill("self_improvement")
        assert si is not None
        assert si.topic.name == "self_improvement"

        psy = registry.get_skill("psychology")
        assert psy is not None
        assert psy.topic.name == "psychology"

    def test_get_skill_unknown(self):
        assert registry.get_skill("nonexistent") is None
