import json
import uuid

from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import (
    ProjectProfileOverrides,
    validate_profile,
)


class ProfileValidationError(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__(f"Invalid profile values: {errors}")
        self.errors = errors


class ProjectService:
    def __init__(self, repo):
        self.repo = repo

    async def create_project(
        self,
        *,
        title: str = "",
        topic: str = "self_improvement",
        focus: str = "",
        overrides: dict | None = None,
    ) -> Project:
        overrides = overrides or {}
        errors = validate_profile(overrides)
        if errors:
            raise ProfileValidationError(errors)
        project = Project(
            topic=topic,
            title=title,
            focus=focus,
            profile_overrides_json=json.dumps(overrides, separators=(",", ":")),
        )
        return await self.repo.create(project)

    async def get(self, project_id: str) -> Project | None:
        return await self.repo.get(project_id)

    async def list_recent(self, limit: int = 50) -> list[Project]:
        return await self.repo.list_recent(limit)

    def _parse_ideas(self, project: Project) -> list[dict]:
        if not project or not project.idea_json:
            return []
        try:
            data = json.loads(project.idea_json)
            return data if isinstance(data, list) else [data]
        except (json.JSONDecodeError, TypeError):
            return []

    def _save_ideas(self, project: Project, ideas: list[dict]) -> Project:
        for idea in ideas:
            if "id" not in idea or not idea["id"]:
                idea["id"] = str(uuid.uuid4())
        project.idea_json = json.dumps(ideas)
        return project

    async def save_ideas(self, project_id: str, ideas: list[dict]) -> Project:
        project = await self.repo.get(project_id)
        if not project:
            raise ValueError("Project not found")
        return await self.repo.update(self._save_ideas(project, ideas))

    async def prepend_ideas(self, project_id: str, new_ideas: list[dict]) -> Project:
        project = await self.repo.get(project_id)
        if not project:
            raise ValueError("Project not found")
        existing = self._parse_ideas(project)
        combined = new_ideas + existing
        return await self.repo.update(self._save_ideas(project, combined))

    async def delete_idea(self, project_id: str, idea_id: str) -> Project:
        project = await self.repo.get(project_id)
        if not project:
            raise ValueError("Project not found")
        ideas = self._parse_ideas(project)
        filtered = [i for i in ideas if i["id"] != idea_id]
        if len(filtered) == len(ideas):
            raise ValueError("Idea not found")
        return await self.repo.update(self._save_ideas(project, filtered))

    async def update_idea(self, project_id: str, idea_id: str, updates: dict) -> Project:
        project = await self.repo.get(project_id)
        if not project:
            raise ValueError("Project not found")
        ideas = self._parse_ideas(project)
        for i, idea in enumerate(ideas):
            if idea["id"] == idea_id:
                ideas[i] = {**idea, **updates}
                break
        else:
            raise ValueError("Idea not found")
        return await self.repo.update(self._save_ideas(project, ideas))

    async def update(self, project_id: str, updates: dict) -> Project:
        project = await self.repo.get(project_id)
        if not project:
            raise ValueError("Project not found")
        for key in (
            "title",
            "topic",
            "focus",
            "default_duration",
            "asset_music_id",
            "asset_font_id",
            "asset_watermark_id",
            "asset_bg_clip_id",
            "asset_outro_clip_id",
        ):
            if key in updates:
                setattr(project, key, updates[key])
        return await self.repo.update(project)

    async def get_idea_by_id(self, project_id: str, idea_id: str) -> dict | None:
        project = await self.repo.get(project_id)
        if not project:
            return None
        ideas = self._parse_ideas(project)
        for idea in ideas:
            if idea["id"] == idea_id:
                return idea
        return None

    async def save_script(self, project_id: str, idea_id: str, script: dict) -> Project:
        return await self.update_idea(project_id, idea_id, {"script_json": json.dumps(script)})

    async def get_script(self, project_id: str, idea_id: str) -> dict | None:
        idea = await self.get_idea_by_id(project_id, idea_id)
        if not idea or not idea.get("script_json"):
            return None
        try:
            return json.loads(idea["script_json"])
        except (json.JSONDecodeError, TypeError):
            return None

    def _decode_overrides(self, project: Project) -> dict:
        try:
            overrides = json.loads(project.profile_overrides_json or "{}")
            return overrides if isinstance(overrides, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    async def save_profile_overrides(
        self, project_id: str, updates: ProjectProfileOverrides
    ) -> Project:
        project = await self.repo.get(project_id)
        if not project:
            raise ValueError("Project not found")
        overrides = self._decode_overrides(project)
        for key, value in updates.model_dump(exclude_none=True).items():
            if value == "":
                overrides.pop(key, None)
            else:
                overrides[key] = value
        errors = validate_profile(overrides)
        if errors:
            raise ProfileValidationError(errors)
        project.profile_overrides_json = json.dumps(overrides, separators=(",", ":"))
        return await self.repo.update(project)

    async def reset_profile_override(self, project_id: str, key: str) -> Project:
        project = await self.repo.get(project_id)
        if not project:
            raise ValueError("Project not found")
        overrides = self._decode_overrides(project)
        overrides.pop(key, None)
        project.profile_overrides_json = json.dumps(overrides, separators=(",", ":"))
        return await self.repo.update(project)

    async def reset_all_profile_overrides(self, project_id: str) -> Project:
        project = await self.repo.get(project_id)
        if not project:
            raise ValueError("Project not found")
        project.profile_overrides_json = "{}"
        return await self.repo.update(project)
