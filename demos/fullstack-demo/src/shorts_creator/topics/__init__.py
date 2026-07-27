from pathlib import Path

from shorts_creator.topics.base import Idea, ParsedScript, ScriptSection, Topic
from shorts_creator.topics.registry import TopicRegistry, TopicSkill
from shorts_creator.topics.skill_topic import SkillTopic

__all__ = [
    "Idea",
    "ParsedScript",
    "ScriptSection",
    "SkillTopic",
    "Topic",
    "TopicRegistry",
    "TopicSkill",
]

_skills_dir = Path(__file__).resolve().parents[3] / "data" / "skills"

registry = TopicRegistry()
registry.load(_skills_dir)
