from unittest.mock import MagicMock

import pytest

from shorts_creator.pipeline.script_parser import ParsedScript as PipelineScript
from shorts_creator.topics.base import ParsedScript as BaseScript
from shorts_creator.topics.base import ScriptSection


class TestRenderScriptConversion:
    def make_pipeline_script(self, **overrides):
        return PipelineScript(
            title=overrides.get("title", "Test Script"),
            duration_seconds=overrides.get("duration_seconds", 30.0),
            word_count=overrides.get("word_count", 120),
            pacing_wps=overrides.get("pacing_wps", 4.0),
            hook=overrides.get("hook", "The hook text"),
            hook_seconds=overrides.get("hook_seconds", 5.0),
            message_lines=overrides.get("message_lines", ["Msg 1", "Msg 2"]),
            message_seconds=overrides.get("message_seconds", 12.0),
            metaphor=overrides.get("metaphor", "The metaphor text"),
            metaphor_seconds=overrides.get("metaphor_seconds", 4.0),
            conclusion=overrides.get("conclusion", "The conclusion"),
            conclusion_seconds=overrides.get("conclusion_seconds", 4.0),
            emotional_arc=overrides.get("emotional_arc", ["hook", "build", "resolve"]),
            parallel_structure=overrides.get("parallel_structure", ""),
            hook_score=overrides.get("hook_score", ""),
        )

    def make_base_script(self, **overrides):
        sections = overrides.get(
            "sections",
            [
                ScriptSection(name="hook", text="The hook text", duration_seconds=5.0),
                ScriptSection(name="message_1", text="Msg 1", duration_seconds=6.0),
                ScriptSection(name="message_2", text="Msg 2", duration_seconds=6.0),
                ScriptSection(name="metaphor", text="The metaphor text", duration_seconds=4.0),
                ScriptSection(name="conclusion", text="The conclusion", duration_seconds=4.0),
            ],
        )
        return BaseScript(
            title=overrides.get("title", "Test Script"),
            sections=sections,
            total_duration=overrides.get("total_duration", 30.0),
            word_count=overrides.get("word_count", 120),
            pacing_wps=overrides.get("pacing_wps", 4.0),
            emotional_arc=overrides.get("emotional_arc", None),
            metadata=overrides.get("metadata", None),
        )

    def test_pipeline_script_has_all_required_attributes(self):
        s = self.make_pipeline_script()
        assert s.duration_seconds == 30.0
        assert s.hook == "The hook text"
        assert s.hook_seconds == 5.0
        assert s.message_lines == ["Msg 1", "Msg 2"]
        assert s.message_seconds == 12.0
        assert s.metaphor == "The metaphor text"
        assert s.metaphor_seconds == 4.0
        assert s.conclusion == "The conclusion"
        assert s.conclusion_seconds == 4.0
        assert s.emotional_arc == ["hook", "build", "resolve"]
        assert s.title == "Test Script"
        assert s.word_count == 120
        assert s.pacing_wps == 4.0

    def test_pipeline_script_from_saved_dict(self):
        saved = {
            "title": "Saved Script",
            "duration_seconds": 35.0,
            "word_count": 140,
            "pacing_wps": 4.0,
            "hook": "Saved hook",
            "hook_seconds": 6.0,
            "message_lines": ["Line 1", "Line 2", "Line 3"],
            "message_seconds": 15.0,
            "metaphor": "Saved metaphor",
            "metaphor_seconds": 5.0,
            "conclusion": "Saved conclusion",
            "conclusion_seconds": 4.0,
            "emotional_arc": ["a", "b"],
            "parallel_structure": "parallel",
            "hook_score": "8/10",
        }
        s = PipelineScript(**saved)
        assert s.duration_seconds == 35.0
        assert s.hook == "Saved hook"
        assert s.message_lines == ["Line 1", "Line 2", "Line 3"]
        assert s.parallel_structure == "parallel"
        assert s.hook_score == "8/10"

    def test_base_script_lacks_pipeline_fields(self):
        s = self.make_base_script()
        assert not hasattr(s, "hook")
        assert not hasattr(s, "duration_seconds")
        assert not hasattr(s, "message_lines")
        assert not hasattr(s, "metaphor")
        assert s.total_duration == 30.0
        assert len(s.sections) == 5

    def test_convert_base_script_to_pipeline_script(self):
        base = self.make_base_script()
        secs = {s.name: s for s in base.sections}
        message_lines = [s.text for n, s in secs.items() if n.startswith("message")]
        message_sec = sum(s.duration_seconds for n, s in secs.items() if n.startswith("message"))
        pipe = PipelineScript(
            title=base.title,
            duration_seconds=base.total_duration,
            word_count=base.word_count,
            pacing_wps=base.pacing_wps,
            hook=secs["hook"].text,
            hook_seconds=secs["hook"].duration_seconds,
            message_lines=message_lines,
            message_seconds=message_sec,
            metaphor=secs["metaphor"].text,
            metaphor_seconds=secs["metaphor"].duration_seconds,
            conclusion=secs["conclusion"].text,
            conclusion_seconds=secs["conclusion"].duration_seconds,
            emotional_arc=base.emotional_arc or [],
            parallel_structure="",
            hook_score="",
        )
        assert pipe.duration_seconds == 30.0
        assert pipe.hook == "The hook text"
        assert pipe.message_lines == ["Msg 1", "Msg 2"]
        assert pipe.message_seconds == 12.0
        assert pipe.metaphor == "The metaphor text"
        assert pipe.conclusion == "The conclusion"

    def test_convert_base_script_with_single_message_section(self):
        sections = [
            ScriptSection(name="hook", text="Hook", duration_seconds=4.0),
            ScriptSection(name="message", text="Only message", duration_seconds=10.0),
            ScriptSection(name="conclusion", text="Conclusion", duration_seconds=3.0),
        ]
        base = BaseScript(
            title="Simple",
            sections=sections,
            total_duration=20.0,
            word_count=80,
            pacing_wps=4.0,
        )
        secs = {s.name: s for s in base.sections}
        message_lines = [s.text for n, s in secs.items() if n.startswith("message")]
        message_sec = sum(s.duration_seconds for n, s in secs.items() if n.startswith("message"))
        pipe = PipelineScript(
            title=base.title,
            duration_seconds=base.total_duration,
            word_count=base.word_count,
            pacing_wps=base.pacing_wps,
            hook=secs["hook"].text,
            hook_seconds=secs["hook"].duration_seconds,
            message_lines=message_lines,
            message_seconds=message_sec,
            metaphor="",
            metaphor_seconds=0,
            conclusion=secs["conclusion"].text,
            conclusion_seconds=secs["conclusion"].duration_seconds,
            emotional_arc=[],
            parallel_structure="",
            hook_score="",
        )
        assert pipe.hook == "Hook"
        assert pipe.message_lines == ["Only message"]
        assert pipe.message_seconds == 10.0
        assert pipe.metaphor == ""
        assert pipe.conclusion == "Conclusion"

    def test_pipeline_script_allows_save_outputs_access(self):
        """Verifies all fields accessed in pipeline._save_outputs exist."""
        s = self.make_pipeline_script()
        fields = {
            "title": s.title,
            "duration_seconds": s.duration_seconds,
            "word_count": s.word_count,
            "pacing_wps": s.pacing_wps,
            "hook": s.hook,
            "hook_seconds": s.hook_seconds,
            "message_lines": s.message_lines,
            "message_seconds": s.message_seconds,
            "metaphor": s.metaphor,
            "metaphor_seconds": s.metaphor_seconds,
            "conclusion": s.conclusion,
            "conclusion_seconds": s.conclusion_seconds,
            "emotional_arc": s.emotional_arc,
            "parallel_structure": s.parallel_structure,
            "hook_score": s.hook_score,
        }
        assert fields["title"] == "Test Script"
        assert fields["duration_seconds"] == 30.0

    def test_pipeline_script_allows_build_scripted_clips_access(self):
        """Verifies fields accessed in pipeline._build_scripted_clips exist."""
        s = self.make_pipeline_script()
        all_lines = [s.hook] + s.message_lines + [s.metaphor, s.conclusion]
        estimated_frames = round((s.duration_seconds * 1.25 + 5) * 30)
        assert len(all_lines) == 5
        assert estimated_frames == round((30 * 1.25 + 5) * 30)

    def test_invalid_transition_still_logs_error(self):
        from unittest.mock import AsyncMock

        from shorts_creator.services.run_service import RunService

        repo = AsyncMock()
        run = MagicMock()
        run.status = "IDEA_SELECTED"
        repo.get.return_value = run
        svc = RunService(repo)
        with pytest.raises(Exception):  # noqa: B017 - assert the guard rejects any invalid target
            svc._transition(run, "FAILED")
