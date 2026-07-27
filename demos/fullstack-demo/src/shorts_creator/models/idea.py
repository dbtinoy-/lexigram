from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class Idea(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    core_message: str
    hook_line: str = ""
    target_audience: str = ""
    emotional_arc: str = ""
    identity_signal: str = ""
    permission_given: str = ""
    share_trigger: str = ""
    quotability_score: float = 5.0
    topic: str = ""
    duration_s: int = 30
    script_json: str | None = None
