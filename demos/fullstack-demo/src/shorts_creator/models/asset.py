from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

ASSET_TYPES = ("music", "font", "image", "clip", "watermark")
CLIP_ROLES = ("background", "intro", "outro", "broll")


def _now() -> datetime:
    return datetime.now(UTC)


class Asset(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    type: str
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    role: str | None = None
    meta: dict = Field(default_factory=dict)
    file_path: str | None = None
