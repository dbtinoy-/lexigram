import re

import pytest
from lexigram.contracts.ai.llm import Completion
from lexigram.result import Ok

from shorts_creator.services.script_service import ScriptService
from shorts_creator.topics import registry
from shorts_creator.topics.base import Idea


class _FakeLLM:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    async def complete(self, messages, **kwargs):
        content = messages[0].content
        self.calls.append((content, kwargs.get("temperature")))
        return Ok(Completion(content=self.outputs.pop(0), model="fake"))


def _bad_script() -> str:
    return re.sub(r'\[PROBLEM - 10s\]\n"[^"]+"\n', "", registry.get("stoic").mock_script())


def _idea() -> Idea:
    return Idea(
        title="The Invictus Mindset",
        core_message="You cannot control what happens, but you can control your response.",
        hook_line="They can take everything from you except your response.",
        identity_signal="Epictetus",
        permission_given="Respond with dignity",
        emotional_arc="victimhood -> ownership -> indomitability",
        target_audience="anyone who feels victimized",
        quotability_score=9.4,
        share_trigger="share",
        topic="stoic",
    )


class TestGenerateScriptRetry:
    @pytest.mark.asyncio
    async def test_retries_once_with_reminder_and_succeeds(self):
        llm = _FakeLLM(["angle notes", _bad_script(), registry.get("stoic").mock_script()])
        service = ScriptService(llm=llm)
        script = await service.generate_script(_idea())
        assert len(llm.calls) == 3  # 1 angle research + 2 script attempts
        assert any("FORMAT REMINDER" in content for content, _ in llm.calls)
        retry_temp = [t for content, t in llm.calls if "FORMAT REMINDER" in content]
        assert retry_temp == [0.3]
        assert script.title == "You Are Not Your Thoughts"

    @pytest.mark.asyncio
    async def test_raises_after_two_failed_attempts(self):
        llm = _FakeLLM(["angle notes", _bad_script(), _bad_script()])
        service = ScriptService(llm=llm)
        with pytest.raises(ValueError, match="PROBLEM"):
            await service.generate_script(_idea())
        assert [t for _, t in llm.calls] == [None, 0.7, 0.3]

    @pytest.mark.asyncio
    async def test_pacing_forwarded_into_prompt_and_forced_onto_script(self):
        llm = _FakeLLM(["angle notes", registry.get("stoic").mock_script()])
        service = ScriptService(llm=llm)
        script = await service.generate_script(_idea(), pacing_wps=2.5)
        assert any("TARGET PACING: 2.5" in content for content, _ in llm.calls)
        assert script.pacing_wps == 2.5

    @pytest.mark.asyncio
    async def test_no_pacing_leaves_parsed_value_untouched(self):
        llm = _FakeLLM(["angle notes", registry.get("stoic").mock_script()])
        service = ScriptService(llm=llm)
        script = await service.generate_script(_idea())
        assert not any("TARGET PACING" in content for content, _ in llm.calls)
        assert script.pacing_wps > 1.0

    @pytest.mark.asyncio
    async def test_voice_forwarded_into_script_prompt(self):
        llm = _FakeLLM(["angle notes", registry.get("stoic").mock_script()])
        service = ScriptService(llm=llm)
        voice = {"audience_persona": "busy founders", "tone_rules": ["no jargon"]}
        await service.generate_script(_idea(), voice=voice)
        assert any("VOICE PROFILE:" in content for content, _ in llm.calls)
        assert any("busy founders" in content for content, _ in llm.calls)

    @pytest.mark.asyncio
    async def test_no_voice_keeps_script_prompt_clean(self):
        llm = _FakeLLM(["angle notes", registry.get("stoic").mock_script()])
        service = ScriptService(llm=llm)
        await service.generate_script(_idea())
        assert not any("VOICE PROFILE" in content for content, _ in llm.calls)
