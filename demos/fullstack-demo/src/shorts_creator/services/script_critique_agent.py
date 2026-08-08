from lexigram.ai.agents import AgentBase
from lexigram.ai.agents.tools.decorator import FunctionTool
from lexigram.contracts.ai.agents import ToolProtocol
from lexigram.contracts.ai.llm import LLMClientProtocol

from shorts_creator.services.critique_tools import CritiqueResult


class ScriptCritiqueAgent(AgentBase):
    name = "script_critique"
    system_prompt = (
        "You are a short-form video script critic. "
        "Analyze scripts for pacing, duration fit, and engagement. "
        "Provide actionable feedback to improve the script."
    )

    def __init__(
        self,
        tools: dict[str, FunctionTool],
        llm: LLMClientProtocol | None = None,
    ) -> None:
        self._tools_map = tools
        self._llm = llm
        super().__init__()

    @property
    def tools(self) -> list[ToolProtocol]:
        return list(self._tools_map.values())

    async def critique_script(
        self,
        script_text: str,
        target_duration: float,
    ) -> CritiqueResult:
        pacing = await self._tools_map["check_pacing"].execute(script_text=script_text)
        duration = await self._tools_map["check_duration"].execute(
            script_text=script_text, target_duration=target_duration
        )
        issues = list(pacing.issues) + list(duration.issues)
        suggestions = list(pacing.suggestions) + list(duration.suggestions)
        score = min(pacing.score, duration.score)
        details = f"Pacing: {pacing.details or 'OK'}; Duration: {duration.details or 'OK'}"
        return CritiqueResult(
            passed=score >= 0.5,
            issues=issues,
            suggestions=suggestions,
            score=score,
            details=details,
        )
