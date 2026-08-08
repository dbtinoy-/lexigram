from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from lexigram.contracts.data import DatabaseProviderProtocol

from shorts_creator.topics import registry as _default_registry
from shorts_creator.topics.registry import TopicRegistry

_PROFILE_FIELDS = frozenset(
    {
        "structure_sections",
        "topic_categories",
        "banned_phrases",
    }
)

_logger = logging.getLogger(__name__)


def _parse_overrides_json(raw: str | None) -> dict:
    """Tolerant parse of a topic_profiles.overrides_json row; corrupt
    or malformed rows collapse to {} instead of raising, falling back to the
    built-in profile on read."""
    try:
        overrides = json.loads(raw or "{}")
    except (TypeError, ValueError):
        _logger.warning("topic_profiles: ignoring corrupt overrides_json row: %r", raw)
        return {}
    if not isinstance(overrides, dict):
        _logger.warning("topic_profiles: ignoring non-object overrides_json row: %r", raw)
        return {}
    return overrides


@dataclass(frozen=True)
class TopicProfile:
    """Effective profile for one topic: registry built-ins merged with persisted overrides."""

    name: str
    structure_sections: list[str] = field(default_factory=list)
    topic_categories: list[str] = field(default_factory=list)
    banned_phrases: list[str] = field(default_factory=list)


class TopicProfileService:
    """Topic profiles: built-in registry topics merged with rows from
    ``topic_profiles.overrides_json``. Overrides are stored in the DB
    only — prompt files on disk are never rewritten."""

    def __init__(
        self,
        db: DatabaseProviderProtocol | None = None,
        topic_registry: TopicRegistry | None = None,
    ):
        self._db = db
        self._registry = topic_registry or _default_registry

    async def list(self) -> list[TopicProfile]:
        profiles: list[TopicProfile] = []
        for topic in self._registry.available:
            profile = await self.get(topic.name)
            if profile is not None:
                profiles.append(profile)
        return profiles

    async def get(self, name: str) -> TopicProfile | None:
        """Return the effective profile merging the registry's built-in topic
        with persisted overrides, or None when the topic is unknown."""
        profile = self._builtin_profile(name)
        if profile is None:
            return None
        if self._db is None:
            return profile
        result = await self._db.execute(
            "SELECT overrides_json FROM topic_profiles WHERE name = ?",
            (name,),
        )
        if not result:
            return profile
        overrides = _parse_overrides_json(result[0]["overrides_json"])
        return self._apply_overrides(profile, overrides)

    async def save_overrides(self, name: str, updates: dict) -> None:
        topic = self._registry.get(name)
        if topic is None:
            raise ValueError(f"unknown topic: {name!r}")
        unknown = set(updates) - _PROFILE_FIELDS
        if unknown:
            raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")
        existing = {}
        if self._db is not None:
            result = await self._db.execute(
                "SELECT overrides_json FROM topic_profiles WHERE name = ?",
                (name,),
            )
            if result:
                existing = _parse_overrides_json(result[0]["overrides_json"])
        merged = {**existing, **updates}
        self._validate(merged)
        if self._db is not None:
            await self._db.execute(
                "INSERT OR REPLACE INTO topic_profiles "
                "(name, overrides_json, created_at, updated_at) VALUES (?, ?, datetime('now'), datetime('now'))",
                (name, json.dumps(merged, separators=(",", ":"))),
            )

    async def count_overrides(self, name: str) -> int:
        """Number of persisted override fields for a profile; 0 when unset or malformed."""
        if self._db is None:
            return 0
        result = await self._db.execute(
            "SELECT overrides_json FROM topic_profiles WHERE name = ?", (name,)
        )
        if not result:
            return 0
        return len(_parse_overrides_json(result[0]["overrides_json"]))

    def _validate(self, overrides: dict) -> None:
        for field_name in ("structure_sections", "topic_categories", "banned_phrases"):
            value = overrides.get(field_name)
            if value is not None and (
                not isinstance(value, list) or not all(isinstance(item, str) for item in value)
            ):
                raise ValueError(f"{field_name} must be a list of strings")

    def _apply_overrides(self, profile: TopicProfile, overrides: dict) -> TopicProfile:
        updates: dict[str, list[str]] = {}
        for field_name in _PROFILE_FIELDS:
            if field_name not in overrides:
                continue
            value = overrides[field_name]
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                _logger.warning(
                    "topic_profiles: ignoring malformed %s override: %r",
                    field_name,
                    value,
                )
                continue
            updates[field_name] = list(value)
        return TopicProfile(
            name=profile.name,
            structure_sections=updates.get("structure_sections", profile.structure_sections),
            topic_categories=updates.get("topic_categories", profile.topic_categories),
            banned_phrases=updates.get("banned_phrases", profile.banned_phrases),
        )

    def _builtin_profile(self, name: str) -> TopicProfile | None:
        topic = self._registry.get(name)
        if topic is None:
            return None
        return TopicProfile(
            name=topic.name,
            structure_sections=list(topic.structure_sections),
            topic_categories=list(topic.topic_categories),
            banned_phrases=list(topic.banned_phrases),
        )
