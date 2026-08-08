from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _now() -> datetime:
    return datetime.now(UTC)


_LEGACY_PROFILE_KEYS = (
    ("default_duration", "duration_seconds"),
    ("format", "format_name"),
    ("caption_style", "caption_style"),
    ("asset_music_id", "asset_music_id"),
    ("asset_font_id", "asset_font_id"),
    ("asset_watermark_id", "asset_watermark_id"),
    ("asset_bg_clip_id", "asset_bg_clip_id"),
    ("asset_outro_clip_id", "asset_outro_clip_id"),
)


def _coerce_duration(value):
    """Coerce a legacy duration to int, mirroring old pydantic coercion."""
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return value


class Project(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    topic: str
    focus: str = ""
    title: str = ""
    idea_json: str | None = None
    profile_overrides_json: str = "{}"

    # Legacy override accessors (pre-JSON storage). Unset values fall back
    # to the same defaults the old columns carried.

    @property
    def format(self) -> str:
        return self._overrides().get("format_name") or "narrated"

    @format.setter
    def format(self, value: str) -> None:
        self._set_override("format_name", value)

    @property
    def caption_style(self) -> str:
        return self._overrides().get("caption_style") or "highlight"

    @caption_style.setter
    def caption_style(self, value: str) -> None:
        self._set_override("caption_style", value)

    @property
    def default_duration(self) -> int | None:
        return _coerce_duration(self._overrides().get("duration_seconds"))

    @default_duration.setter
    def default_duration(self, value: int | None) -> None:
        self._set_override("duration_seconds", value)

    @property
    def asset_music_id(self) -> str | None:
        return self._overrides().get("asset_music_id")

    @asset_music_id.setter
    def asset_music_id(self, value: str | None) -> None:
        self._set_override("asset_music_id", value)

    @property
    def asset_font_id(self) -> str | None:
        return self._overrides().get("asset_font_id")

    @asset_font_id.setter
    def asset_font_id(self, value: str | None) -> None:
        self._set_override("asset_font_id", value)

    @property
    def asset_watermark_id(self) -> str | None:
        return self._overrides().get("asset_watermark_id")

    @asset_watermark_id.setter
    def asset_watermark_id(self, value: str | None) -> None:
        self._set_override("asset_watermark_id", value)

    @property
    def asset_bg_clip_id(self) -> str | None:
        return self._overrides().get("asset_bg_clip_id")

    @asset_bg_clip_id.setter
    def asset_bg_clip_id(self, value: str | None) -> None:
        self._set_override("asset_bg_clip_id", value)

    @property
    def asset_outro_clip_id(self) -> str | None:
        return self._overrides().get("asset_outro_clip_id")

    @asset_outro_clip_id.setter
    def asset_outro_clip_id(self, value: str | None) -> None:
        self._set_override("asset_outro_clip_id", value)

    @model_validator(mode="before")
    @classmethod
    def _fold_legacy_overrides(cls, data):
        """Fold legacy override kwargs into profile_overrides_json."""
        if not isinstance(data, dict):
            return data
        legacy = {
            profile_key: data.pop(legacy_key)
            for legacy_key, profile_key in _LEGACY_PROFILE_KEYS
            if legacy_key in data and data[legacy_key] not in (None, "")
        }
        if not legacy:
            return data
        if "duration_seconds" in legacy:
            duration = _coerce_duration(legacy["duration_seconds"])
            if duration is None:
                legacy.pop("duration_seconds")
            else:
                legacy["duration_seconds"] = duration
        try:
            merged = json.loads(data.pop("profile_overrides_json", None) or "{}")
        except (TypeError, ValueError):
            merged = {}
        merged.update(legacy)
        data["profile_overrides_json"] = json.dumps(merged, separators=(",", ":"))
        return data

    def _overrides(self) -> dict:
        try:
            return json.loads(self.profile_overrides_json or "{}")
        except (TypeError, ValueError):
            return {}

    def _set_override(self, key: str, value) -> None:
        merged = self._overrides()
        if value is None or value == "":
            merged.pop(key, None)
        else:
            merged[key] = value
        self.profile_overrides_json = json.dumps(merged, separators=(",", ":"))
