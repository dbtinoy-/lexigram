from typing import TYPE_CHECKING

from lexigram.contracts.ai.llm import ChatMessage, LLMClientProtocol, Role

from shorts_creator.pipeline.seo import generate_seo_metadata, research_content_angles
from shorts_creator.services.core import AppConfig
from shorts_creator.services.critique_tools import CritiqueResult
from shorts_creator.topics import Idea, ParsedScript, registry

if TYPE_CHECKING:
    from shorts_creator.services.script_critique_agent import ScriptCritiqueAgent


class ScriptService:
    def __init__(self, config: AppConfig | None = None, llm: LLMClientProtocol | None = None):
        self._last_script: ParsedScript | None = None
        self.config = config
        self.llm = llm
        self.critique_agent: ScriptCritiqueAgent | None = None

    async def generate_script(
        self,
        idea: Idea,
        format_name: str = "",
        pacing_wps: float | None = None,
        voice: dict | None = None,
    ) -> ParsedScript:
        if self.llm is None:
            raise RuntimeError("LLM client not available — check LLM provider configuration")
        st = registry.get(idea.topic) if idea.topic else None
        if not st:
            st = next(iter(registry.available))

        angle_context = await research_content_angles(
            idea.title,
            idea.core_message,
            self.llm,
        )
        prompt = st.build_script_prompt(
            idea=idea,
            angle_context=angle_context,
            format_name=format_name,
            pacing_wps=pacing_wps,
            voice=voice,
        )
        reminder = (
            "\n\nFORMAT REMINDER: Respond with exactly the template structure. "
            "Every section must be a [SECTION - Ns] header on its own line, "
            "followed by the section text on the next line wrapped in double "
            "quotes. Do not omit, rename, or merge any section."
        )
        last_exc: ValueError | None = None
        for attempt in range(2):
            content = prompt + (reminder if attempt else "")
            result = await self.llm.complete(
                messages=[ChatMessage(role=Role.USER, content=content)],
                model="",
                temperature=0.7 if attempt == 0 else 0.3,
            )
            if result.is_err():
                last_exc = ValueError(str(result.unwrap_err()))
                continue
            try:
                script = st.parse_script(result.unwrap().content)
            except ValueError as exc:
                last_exc = exc
                continue
            if pacing_wps:
                script.pacing_wps = pacing_wps
            self._last_script = script
            return script
        if last_exc is not None:
            raise last_exc
        raise ValueError("Could not parse script output")

    async def generate_seo(self, script: ParsedScript) -> dict:
        meta = await generate_seo_metadata(script, self.llm)
        return meta

    async def critique_script(
        self,
        script_text: str,
        target_duration: float = 30.0,
    ) -> CritiqueResult:
        if self.critique_agent is None:
            return CritiqueResult()
        return await self.critique_agent.critique_script(script_text, target_duration)

    @property
    def last_script(self) -> ParsedScript | None:
        return self._last_script
