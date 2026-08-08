from pathlib import Path
from typing import Any

from shorts_creator.contracts.capabilities import CapabilityVocabularyError
from shorts_creator.contracts.errors import ContractLoadError
from shorts_creator.topics.base import Topic
from shorts_creator.topics.skill_topic import SkillTopic


class TopicSkill:
    """Wraps a Topic as a skill for discovery and composition."""

    def __init__(self, topic: Topic):
        self._topic = topic

    @property
    def name(self) -> str:
        return f"topic_{self._topic.name}"

    @property
    def description(self) -> str:
        return (
            f"Generate {self._topic.label} video scripts. "
            f"{self._topic.description} "
            f"Topics: {', '.join(self._topic.topic_categories)}"
        )

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action", "describe")
        if action == "describe":
            return self.description
        return f"Topic '{self._topic.name}' executed action '{action}'"

    @property
    def topic(self) -> Topic:
        return self._topic


class TopicRegistry:
    """Registry of all available Topics loaded from SKILL.md directories."""

    def __init__(self):
        self._topics: dict[str, Topic] = {}
        self._skills: dict[str, TopicSkill] = {}
        self._errors: list[tuple[Path, Exception]] = []

    def load(self, skills_dir: str | Path, strict: bool = False) -> int:
        count = 0
        self._errors = []
        failures: list[tuple[Path, Exception]] = []
        for md_path in Path(skills_dir).glob("*/SKILL.md"):
            skill_dir = md_path.parent
            try:
                topic = SkillTopic(skill_dir)
                self.register(topic)
                count += 1
            except CapabilityVocabularyError as exc:
                failures.append((skill_dir, exc))
            except Exception:  # noqa: BLE001, S112 - skip broken, non-contract dirs
                continue
        if strict and failures:
            raise ContractLoadError(failures)
        self._errors = failures
        return count

    def errors(self) -> list[tuple[Path, Exception]]:
        return list(self._errors)

    def register(self, topic: Topic) -> TopicSkill:
        self._topics[topic.name] = topic
        skill = TopicSkill(topic)
        self._skills[topic.name] = skill
        return skill

    def get(self, name: str) -> Topic | None:
        return self._topics.get(name)

    def get_skill(self, name: str) -> TopicSkill | None:
        return self._skills.get(name)

    @property
    def available(self) -> list[Topic]:
        return list(self._topics.values())

    @property
    def skills(self) -> list[TopicSkill]:
        return list(self._skills.values())

    def build_pipeline(self, topic_name: str, steps: list[str]) -> dict[str, Any] | None:
        skill = self.get_skill(topic_name)
        if not skill:
            return None
        return {"name": f"{topic_name}_pipeline", "steps": steps, "skill": skill}

    def names(self) -> list[str]:
        return list(self._topics.keys())

    def choices(self) -> list[dict]:
        return [
            {"name": t.name, "label": t.label, "description": t.description}
            for t in self._topics.values()
        ]
