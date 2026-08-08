from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RunStatus(str, Enum):
    DRAFT = "draft"
    IDEA_SELECTED = "idea_selected"
    SCRIPT_READY = "script_ready"
    QUEUED = "queued"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


def _now() -> datetime:
    return datetime.now(UTC)


class Run(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    title: str = ""
    status: RunStatus = RunStatus.DRAFT
    selected_idea_id: str | None = None
    stage_progress: dict[str, int] = Field(default_factory=dict)
    settings_snapshot_json: str | None = None
    output_path: str | None = None
    duration_s: float | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
