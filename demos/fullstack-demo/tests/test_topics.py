"""Tests for script types — registry, parsing, and type-specific behavior."""

from shorts_creator.topics import Idea, ParsedScript, registry


class TestRegistry:
    def test_has_both_types(self):
        names = registry.names()
        assert "self_improvement" in names
        assert "psychology" in names

    def test_get_returns_type(self):
        si = registry.get("self_improvement")
        assert si is not None
        assert si.name == "self_improvement"

        psy = registry.get("psychology")
        assert psy is not None
        assert psy.name == "psychology"

    def test_get_unknown_returns_none(self):
        assert registry.get("nonexistent") is None

    def test_available_returns_all(self):
        assert len(registry.available) >= 2

    def test_choices_format(self):
        choices = registry.choices()
        assert len(choices) >= 2
        names = {c["name"] for c in choices}
        assert {"self_improvement", "psychology"}.issubset(names)


class TestSelfImprovementParsing:
    def setup_method(self):
        self.st = registry.get("self_improvement")

    def test_parse_ideas(self):
        raw = self.st.mock_ideas()
        ideas = self.st.parse_ideas(raw)
        assert len(ideas) >= 1
        for idea in ideas:
            assert isinstance(idea, Idea)
            assert idea.title
            assert idea.core_message
            assert isinstance(idea.quotability_score, (int, float))

    def test_parse_script(self):
        raw = self.st.mock_script()
        script = self.st.parse_script(raw)
        assert isinstance(script, ParsedScript)
        assert script.title
        assert len(script.sections) >= 4
        assert script.total_duration > 0
        assert script.word_count > 0

    def test_script_sections_have_expected_names(self):
        raw = self.st.mock_script()
        script = self.st.parse_script(raw)
        names = [s.name for s in script.sections]
        assert "hook" in names
        assert "message" in names or "metaphor" in names
        assert "conclusion" in names
        assert "cta" not in names


class TestPsychologyParsing:
    def setup_method(self):
        self.st = registry.get("psychology")

    def test_parse_ideas(self):
        raw = self.st.mock_ideas()
        ideas = self.st.parse_ideas(raw)
        assert len(ideas) >= 1
        for idea in ideas:
            assert isinstance(idea, Idea)
            assert idea.title
            assert idea.core_message

    def test_parse_script(self):
        raw = self.st.mock_script()
        script = self.st.parse_script(raw)
        assert isinstance(script, ParsedScript)
        assert script.title
        assert len(script.sections) >= 4
        assert script.total_duration > 0
        assert script.word_count > 0

    def test_script_sections_have_expected_names(self):
        raw = self.st.mock_script()
        script = self.st.parse_script(raw)
        names = [s.name for s in script.sections]
        assert "hook" in names
        assert "context" in names
        assert "explanation" in names
        assert "reflection" in names


class TestStoicSectionHeaderVariants:
    def setup_method(self):
        self.st = registry.get("stoic")
        assert self.st is not None, "stoic skill should be loaded"

    def test_no_dash_header_parses(self):
        raw = self.st.mock_script().replace("[PROBLEM - 10s]", "[PROBLEM 10s]")
        script = self.st.parse_script(raw)
        names = [s.name for s in script.sections]
        assert "problem" in names

    def test_en_dash_header_parses(self):
        raw = self.st.mock_script().replace("[PROBLEM - 10s]", "[PROBLEM – 10s]")
        script = self.st.parse_script(raw)
        names = [s.name for s in script.sections]
        assert "problem" in names


class TestTypeDifferences:
    def setup_method(self):
        self.si = registry.get("self_improvement")
        self.psy = registry.get("psychology")

    def test_different_topic_categories(self):
        assert self.si.topic_categories != self.psy.topic_categories

    def test_different_ideas(self):
        si_raw = self.si.mock_ideas()
        psy_raw = self.psy.mock_ideas()
        si_ideas = self.si.parse_ideas(si_raw)
        psy_ideas = self.psy.parse_ideas(psy_raw)
        si_titles = {i.title.lower() for i in si_ideas}
        psy_titles = {i.title.lower() for i in psy_ideas}
        assert si_titles != psy_titles


class TestGenerateIdeasAPI:
    """Tests the idea generation logic used by /api/ideas/generate."""

    def test_generate_with_self_improvement(self):
        st = registry.get("self_improvement")
        raw = st.mock_ideas()
        ideas = st.parse_ideas(raw)
        assert len(ideas) >= 1
        assert all(i.topic == "self_improvement" for i in ideas)

    def test_generate_with_psychology(self):
        st = registry.get("psychology")
        raw = st.mock_ideas()
        ideas = st.parse_ideas(raw)
        assert len(ideas) >= 1
        assert all(i.topic == "psychology" for i in ideas)

    def test_idea_topic_preserved(self):
        for type_name in ("self_improvement", "psychology"):
            st = registry.get(type_name)
            raw = st.mock_ideas()
            ideas = st.parse_ideas(raw)
            assert all(i.topic == type_name for i in ideas)
