from __future__ import annotations

import json
from typing import Any

from shorts_creator.contracts.issues import ContractIssue, Severity
from shorts_creator.contracts.matcher import is_valid_pair, validate_pair
from shorts_creator.formats import registry as format_registry
from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import (
    PROFILE_FIELD_NAMES,
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
    validate_profile,
)
from shorts_creator.services.core import AppConfig
from shorts_creator.services.settings_store import SettingsStore
from shorts_creator.topics import registry as topics_registry

OVERRIDE_FIELDS = frozenset(PROFILE_FIELD_NAMES) - {"reel_width", "reel_height"}

_ASSET_GLOBAL_KEYS = {
    "asset_music_id": "asset_default_music_id",
    "asset_font_id": "asset_default_font_id",
    "asset_watermark_id": "asset_default_watermark_id",
    "asset_bg_clip_id": "asset_default_bg_clip_id",
    "asset_outro_clip_id": "asset_default_outro_clip_id",
}

_ASSET_ROLE_FIELDS = {
    "music": "asset_music_id",
    "font": "asset_font_id",
    "watermark": "asset_watermark_id",
    "bg_clip": "asset_bg_clip_id",
    "outro_clip": "asset_outro_clip_id",
}


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def resolve_global_settings(config: AppConfig, values: dict[str, Any] | None) -> dict[str, Any]:
    """Resolve the global tier: valid app_settings values, falling back to
    AppConfig/hard defaults. Shared by resolve paths of ProjectProfileService."""
    values = values or {}
    duration = _as_float(values.get("default_duration"))
    if duration is None or duration <= 0:
        duration = config.default_duration
    return {
        "default_duration": duration,
        "default_caption_style": _as_str(values.get("default_caption_style")) or "highlight",
        "asset_default_music_id": _as_str(values.get("asset_default_music_id")),
        "asset_default_font_id": _as_str(values.get("asset_default_font_id")),
        "asset_default_watermark_id": _as_str(values.get("asset_default_watermark_id")),
        "asset_default_bg_clip_id": _as_str(values.get("asset_default_bg_clip_id")),
        "asset_default_outro_clip_id": _as_str(values.get("asset_default_outro_clip_id")),
    }


def _resolved(value: Any, source: ProfileSource) -> ResolvedSetting:
    return ResolvedSetting(
        value=value, source=source, is_overridden=source is ProfileSource.PROJECT
    )


class ProjectProfileService:
    """Unified, provenance-aware project profile resolution.

    Precedence per field: project override → format definition → global
    settings → AppConfig/built-in defaults.
    """

    def __init__(
        self,
        config: AppConfig,
        global_store: SettingsStore | None = None,
    ):
        self._config = config
        self._global_store = global_store

    async def resolve(
        self, project: Project, global_values: dict[str, Any] | None = None
    ) -> EffectiveProjectProfile:
        """Resolve the effective profile for a project."""
        overrides = self._parse_overrides(project)
        if global_values is None:
            global_values = (
                await self._global_store.get_global_values()
                if self._global_store is not None
                else {}
            )
        global_ = resolve_global_settings(self._config, global_values)

        format_name = self._resolve_format(overrides, project.topic)
        fmt = format_registry.get(format_name.value)

        caption_style = (
            _resolved("", ProfileSource.BUILT_IN)
            if fmt is not None and not fmt.caption_styles
            else self._resolve_caption(overrides, global_, global_values, fmt)
        )

        return EffectiveProjectProfile(
            duration_seconds=self._resolve_duration(overrides, fmt, global_, global_values),
            caption_style=caption_style,
            format_name=format_name,
            **self._resolve_assets(overrides, global_, global_values),
            bg_source=self._resolve_scalar_str(overrides, "bg_source"),
            bg_mode=self._resolve_scalar_str(overrides, "bg_mode"),
            stock_provider=self._resolve_scalar_str(overrides, "stock_provider"),
            topic=_resolved(project.topic, ProfileSource.PROJECT),
            reel_width=_resolved(self._config.reel_width, ProfileSource.BUILT_IN),
            reel_height=_resolved(self._config.reel_height, ProfileSource.BUILT_IN),
            pacing_wps=self._resolve_pacing_wps(overrides, fmt),
            hook_text=self._resolve_scalar_str(overrides, "hook_text"),
            outro_text=self._resolve_scalar_str(overrides, "outro_text"),
            audience_persona=self._resolve_scalar_str(overrides, "audience_persona"),
            banned_topics=self._resolve_scalar_list_str(overrides, "banned_topics"),
            tone_rules=self._resolve_scalar_list_str(overrides, "tone_rules"),
            voice_preset=self._resolve_scalar_str(overrides, "voice_preset"),
            hook_lead_in_seconds=self._resolve_hook_lead_in(overrides),
            sections=self._resolve_sections(overrides, fmt),
            section_texts=self._resolve_scalar_dict_str(overrides, "section_texts"),
            style=self._resolve_scalar_dict(overrides, "style"),
            palette=self._resolve_palette(overrides, fmt),
            layout=self._resolve_layout(overrides, fmt),
            stages=self._resolve_stages(overrides, fmt),
            stage_accents=self._resolve_scalar_dict(overrides, "stage_accents"),
            section_holds=self._resolve_scalar_dict(overrides, "section_holds"),
            background_motion=self._resolve_scalar_str(overrides, "background_motion"),
            emphasis_style=self._resolve_scalar_str(overrides, "emphasis_style"),
            loudness_target_lufs=self._resolve_scalar_number(overrides, "loudness_target_lufs"),
            audio_normalize=self._resolve_scalar_bool(overrides, "audio_normalize"),
        )

    async def validate_pair_for_project(self, project: Project) -> list[ContractIssue]:
        """Contract issues for the project's effective topic×format pair.

        Combines the pure pair validation (script/voice/pipeline/objectives)
        with project-armed checks: the resolved caption style must be in the
        format's supported styles (REQ_STYLE), every asset role the format
        requires must resolve to a selected asset (REQ_ASSET), and the
        resolved format must still be loaded (FORMAT_NOT_LOADED). An unknown
        topic yields no issues (there is no contract to check against).
        """
        profile = await self.resolve(project)
        issues: list[ContractIssue] = []
        if profile.format_name is None:
            return issues
        fmt = format_registry.get(profile.format_name.value)
        if fmt is None:
            issues.append(
                ContractIssue(
                    Severity.ERROR,
                    "FORMAT_NOT_LOADED",
                    f"resolved format {profile.format_name.value!r} is not loaded; "
                    "the registry may have changed since this project was created",
                )
            )
            return issues

        topic = topics_registry.get(project.topic)
        if topic is None:
            return issues
        issues.extend(validate_pair(topic.to_contract_side(), fmt.to_contract_side()))

        style = profile.caption_style.value if profile.caption_style else None
        if style and style not in fmt.caption_styles:
            issues.append(
                ContractIssue(
                    Severity.ERROR,
                    "REQ_STYLE",
                    f"resolved caption style {style!r} is not supported by format "
                    f"{fmt.name!r}; supported: {fmt.caption_styles}",
                )
            )

        for role in fmt.to_contract_side().requires_assets:
            field = _ASSET_ROLE_FIELDS.get(role)
            setting = getattr(profile, field) if field else None
            value = setting.value if setting else None
            if value is None or value == "":
                issues.append(
                    ContractIssue(
                        Severity.ERROR,
                        "REQ_ASSET",
                        f"format {fmt.name!r} requires asset role {role!r} but the "
                        "project's effective profile has none selected",
                    )
                )

        return issues

    async def reset_override(self, project: Project, key: str) -> Project:
        """Return a copy of the project with the override key removed."""
        overrides = self._parse_overrides(project)
        overrides.pop(key, None)
        return project.model_copy(
            update={"profile_overrides_json": json.dumps(overrides, separators=(",", ":"))}
        )

    @staticmethod
    def validate(values: dict | EffectiveProjectProfile) -> dict[str, str]:
        """Validate a profile dict or effective profile; returns {field: error}."""
        if isinstance(values, EffectiveProjectProfile):
            values = values.snapshot_dict()
        return validate_profile(values)

    def _resolve_duration(
        self,
        overrides: dict,
        format_def,
        global_: dict,
        raw_global: dict,
    ) -> ResolvedSetting[float]:
        if "duration_seconds" in overrides:
            value = _as_float(overrides["duration_seconds"])
            if value is not None and value > 0:
                return _resolved(value, ProfileSource.PROJECT)
        if format_def is not None and format_def.duration_range is not None:
            lo, hi = format_def.duration_range
            return _resolved(float((lo + hi) // 2), ProfileSource.FORMAT)
        raw = _as_float(raw_global.get("default_duration"))
        if raw is not None and raw > 0:
            return _resolved(raw, ProfileSource.GLOBAL)
        return _resolved(global_["default_duration"], ProfileSource.BUILT_IN)

    def _resolve_caption(
        self, overrides: dict, global_: dict, raw_global: dict, fmt
    ) -> ResolvedSetting:
        if "caption_style" in overrides:
            value = _as_str(overrides["caption_style"])
            if value is not None:
                return _resolved(value, ProfileSource.PROJECT)
        if fmt is not None and fmt.default_caption_style:
            return _resolved(fmt.default_caption_style, ProfileSource.BUILT_IN)
        value = _as_str(raw_global.get("default_caption_style"))
        if value is not None:
            return _resolved(value, ProfileSource.GLOBAL)
        return _resolved(global_["default_caption_style"], ProfileSource.BUILT_IN)

    def _resolve_format(self, overrides: dict, topic_name: str | None = None) -> ResolvedSetting:
        """Resolve the effective format: project override → topic default
        (built-in) → first topic-compatible registered format → legacy
        ``"narrated"``. The topic tiers are built-in defaults, exactly where
        ``"narrated"`` sits today."""
        if "format_name" in overrides:
            value = _as_str(overrides["format_name"])
            if value is not None:
                return _resolved(value, ProfileSource.PROJECT)
        if topic_name is not None:
            topic = topics_registry.get(topic_name)
            if topic is not None:
                default = topic.default_format
                if default is not None and format_registry.has(default):
                    return _resolved(default, ProfileSource.BUILT_IN)
                for fmt in format_registry.available:
                    if _format_compatible(fmt, topic):
                        return _resolved(fmt.name, ProfileSource.BUILT_IN)
        return _resolved("narrated", ProfileSource.BUILT_IN)

    def _resolve_assets(
        self, overrides: dict, global_: dict, raw_global: dict
    ) -> dict[str, ResolvedSetting]:
        assets = {}
        for field, global_key in _ASSET_GLOBAL_KEYS.items():
            if field in overrides:
                value = _as_str(overrides[field])
                if value is not None:
                    assets[field] = _resolved(value, ProfileSource.PROJECT)
                else:
                    assets[field] = _resolved(None, ProfileSource.BUILT_IN)
                continue
            value = _as_str(raw_global.get(global_key))
            if value is not None:
                assets[field] = _resolved(value, ProfileSource.GLOBAL)
            else:
                assets[field] = _resolved(global_[global_key], ProfileSource.BUILT_IN)
        for field in (
            "media_url_music",
            "media_url_bg_clip",
            "media_url_outro",
            "media_url_watermark",
        ):
            value = _as_str(overrides.get(field))
            assets[field] = (
                _resolved(value, ProfileSource.PROJECT)
                if value is not None
                else _resolved(None, ProfileSource.BUILT_IN)
            )
        return assets

    def _resolve_pacing_wps(self, overrides: dict, format_def) -> ResolvedSetting:
        if "pacing_wps" in overrides:
            value = _as_float(overrides["pacing_wps"])
            if value is not None and value > 0:
                if format_def is not None:
                    lo, hi = format_def.pacing_wps_range
                    value = max(lo, min(hi, value))
                return _resolved(value, ProfileSource.PROJECT)
        return _resolved(None, ProfileSource.BUILT_IN)

    def _resolve_scalar_str(self, overrides: dict, key: str) -> ResolvedSetting:
        value = _as_str(overrides.get(key))
        if value is not None:
            return _resolved(value, ProfileSource.PROJECT)
        return _resolved(None, ProfileSource.BUILT_IN)

    def _resolve_scalar_list_str(self, overrides: dict, key: str) -> ResolvedSetting:
        value = overrides.get(key)
        if isinstance(value, list) and all(isinstance(s, str) for s in value):
            return _resolved(list(value), ProfileSource.PROJECT)
        return _resolved(None, ProfileSource.BUILT_IN)

    def _resolve_hook_lead_in(self, overrides: dict) -> ResolvedSetting:
        if "hook_lead_in_seconds" in overrides:
            value = _as_float(overrides["hook_lead_in_seconds"])
            if value is not None:
                return _resolved(max(0.0, min(3.0, value)), ProfileSource.PROJECT)
        return _resolved(None, ProfileSource.BUILT_IN)

    def _resolve_scalar_dict(self, overrides: dict, key: str) -> ResolvedSetting:
        value = overrides.get(key)
        if isinstance(value, dict):
            return _resolved(dict(value), ProfileSource.PROJECT)
        return _resolved(None, ProfileSource.BUILT_IN)

    def _resolve_scalar_dict_str(self, overrides: dict, key: str) -> ResolvedSetting:
        value = overrides.get(key)
        if isinstance(value, dict) and all(
            isinstance(k, str) and isinstance(v, str) for k, v in value.items()
        ):
            return _resolved(dict(value), ProfileSource.PROJECT)
        return _resolved(None, ProfileSource.BUILT_IN)

    def _resolve_scalar_number(self, overrides: dict, key: str) -> ResolvedSetting:
        value = _as_float(overrides.get(key))
        if value is not None:
            return _resolved(value, ProfileSource.PROJECT)
        return _resolved(None, ProfileSource.BUILT_IN)

    def _resolve_scalar_bool(self, overrides: dict, key: str) -> ResolvedSetting:
        value = overrides.get(key)
        if isinstance(value, bool):
            return _resolved(value, ProfileSource.PROJECT)
        return _resolved(None, ProfileSource.BUILT_IN)

    def _resolve_sections(self, overrides: dict, format_def) -> ResolvedSetting:
        value = overrides.get("sections")
        if isinstance(value, list) and all(isinstance(s, str) for s in value):
            return _resolved(list(value), ProfileSource.PROJECT)
        if format_def is not None:
            script_caps = set(format_def.requires.get("script") or [])
            if "top_items" in script_caps:
                return _resolved(["top_items"], ProfileSource.FORMAT)
        return _resolved(None, ProfileSource.BUILT_IN)

    def _resolve_palette(self, overrides: dict, format_def) -> ResolvedSetting:
        merged = dict(getattr(format_def, "palette", {}) or {}) if format_def is not None else {}
        value = overrides.get("palette")
        if isinstance(value, dict):
            merged.update({k: v for k, v in value.items() if v is not None})
            return _resolved(merged, ProfileSource.PROJECT)
        if merged:
            return _resolved(merged, ProfileSource.FORMAT)
        return _resolved(None, ProfileSource.BUILT_IN)

    def _resolve_layout(self, overrides: dict, format_def) -> ResolvedSetting:
        if "layout" not in overrides:
            return _resolved(None, ProfileSource.BUILT_IN)
        value = overrides.get("layout")
        if not isinstance(value, dict):
            return _resolved(None, ProfileSource.BUILT_IN)
        resolved = dict(value)
        declared = dict(getattr(format_def, "layout", {}) or {}) if format_def is not None else {}
        for key, default in (("block_width_pct", 80), ("numbered_scale", 1.6)):
            rng = declared.get(key) or []
            if isinstance(rng, (list, tuple)) and len(rng) == 2 and key in resolved:
                resolved[key] = max(rng[0], min(rng[1], resolved[key]))
        return _resolved(resolved, ProfileSource.PROJECT)

    def _resolve_stages(self, overrides: dict, format_def) -> ResolvedSetting:
        required = (
            set(format_def.requires.get("pipeline") or []) if format_def is not None else set()
        )
        base = {
            "music": "music_beat" in required,
            "outro": "outro" in required,
            "watermark": False,
            "background": "background" in required,
        }
        value = overrides.get("stages")
        if isinstance(value, dict):
            merged = dict(base)
            merged.update({k: v for k, v in value.items() if isinstance(v, bool)})
            for stage, required_flag in (
                ("music", "music_beat" in required),
                ("outro", "outro" in required),
                ("background", "background" in required),
            ):
                if required_flag:
                    merged[stage] = True
            return _resolved(merged, ProfileSource.PROJECT)
        if any(base.values()):
            return _resolved(base, ProfileSource.FORMAT)
        return _resolved(None, ProfileSource.BUILT_IN)

    @staticmethod
    def _parse_overrides(project: Project) -> dict:
        try:
            overrides = json.loads(project.profile_overrides_json or "{}")
        except (TypeError, ValueError):
            overrides = {}
        if not isinstance(overrides, dict):
            return {}
        return {key: value for key, value in overrides.items() if key in OVERRIDE_FIELDS}


def _format_compatible(fmt, topic) -> bool:
    """True when the topic's contract satisfies the format's contract."""
    if topic is None:
        return True
    return is_valid_pair(topic.to_contract_side(), fmt.to_contract_side())


def compatible_formats(topic_name: str | None) -> list[str]:
    """Names of registered formats compatible with the topic's contract,
    in registry order. All formats are compatible when there is no topic."""
    topic = topics_registry.get(topic_name) if topic_name is not None else None
    return [fmt.name for fmt in format_registry.available if _format_compatible(fmt, topic)]


def compatible_formats_by_topic() -> dict[str, list[str]]:
    return {topic.name: compatible_formats(topic.name) for topic in topics_registry.available}


def pair_block_message(topic_name: str | None, format_name: str | None) -> str | None:
    """First ERROR-severity contract message for a topic×format pair, or None
    when the pair is valid (or either side is unknown to the registries)."""
    topic = topics_registry.get(topic_name) if topic_name else None
    fmt = format_registry.get(format_name) if format_name else None
    if topic is None or fmt is None:
        return None
    for issue in validate_pair(topic.to_contract_side(), fmt.to_contract_side()):
        if issue.severity is Severity.ERROR:
            return f"{issue.code}: {issue.message}"
    return None
