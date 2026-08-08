from lexigram.contracts.ai.llm import ChatMessage, LLMClientProtocol, Role

from shorts_creator.pipeline.seo import research_keywords
from shorts_creator.services.core import AppConfig
from shorts_creator.topics import Idea, registry


class IdeaService:
    def __init__(self, config: AppConfig | None = None, llm: LLMClientProtocol | None = None):
        self.config = config
        self.llm = llm

    async def generate_ideas(
        self,
        count: int,
        focus: str,
        topic: str = "self_improvement",
        voice: dict | None = None,
    ) -> list[Idea]:
        if self.llm is None:
            raise RuntimeError("LLM client not available — check LLM provider configuration")
        st = registry.get(topic)
        if not st:
            st = next(iter(registry.available))

        seo_context = await research_keywords(focus, self.llm)
        prompt = st.build_idea_prompt(
            count=count,
            focus=focus,
            seo_context=seo_context,
            voice=voice,
        )
        result = await self.llm.complete(
            messages=[ChatMessage(role=Role.USER, content=prompt)],
            model="",
            temperature=0.7,
        )
        if result.is_err():
            raise RuntimeError(f"LLM idea generation failed: {result.unwrap_err()}")
        raw = result.unwrap().content
        return st.parse_ideas(raw)

    async def generate_and_pick(
        self,
        count: int,
        focus: str,
        topic: str = "self_improvement",
        voice: dict | None = None,
    ) -> Idea:
        ideas = await self.generate_ideas(count, focus, topic, voice)
        if not ideas:
            msg = "Idea generation produced no parseable ideas"
            raise RuntimeError(msg)
        return max(ideas, key=lambda i: i.quotability_score)
