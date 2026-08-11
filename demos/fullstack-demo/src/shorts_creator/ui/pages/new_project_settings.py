import json

from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
)
from shorts_creator.services.project_profile_service import compatible_formats_by_topic
from shorts_creator.topics import registry
from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.pages.new_project_main import composer_preview_js
from shorts_creator.ui.pages.new_project_panels import (
    _active_classes,
    _composer_value,
    _content_panel,
    _media_panel,
    _phase2_panel,
    _placement_panel,
    _presets_panel,
    _spec_panel,
    _style_panel,
)
from shorts_creator.ui.pages.new_project_preview import (
    _preview_phone,
    preview_styles,
)
from shorts_creator.ui.pages.new_project_profile import _profile_strip
from shorts_creator.ui.pages.new_project_wizard import (
    _wizard_caption_field,
    _wizard_duration_field,
    _wizard_format_field,
    _wizard_globals_js,
)

# ──────────────────────────────────────────────
# Guided project creation
# ──────────────────────────────────────────────


def project_settings_form(
    project,
    profile: EffectiveProjectProfile,
    asset_options: dict[str, list[tuple[str, str]]] | None = None,
    stock_providers: list[str] | None = None,
    builtin_profile: EffectiveProjectProfile | None = None,
):
    """Composer-driven settings editor for an existing project.

    Reuses the same composer panels + live phone preview as the create page,
    plus the editable wizard fields (format/duration/caption style).
    The profile-driven hidden inputs carry no `name`, so they never affect the
    save payload; untouched knobs keep inherited provenance instead of being
    persisted as project overrides. Rendered in the project shell by the
    ProjectSettingsController (header + Settings tab).
    builtin_profile is the same resolution with the project's overrides
    suppressed; it seeds the pacing knobs' data_builtin (reset target)."""
    active_classes = _active_classes()
    topic = registry.get(profile.topic.value) if profile.topic else None

    hidden_inputs = []
    composites = [
        ("new-project-type", profile.topic.value if profile.topic else "self_improvement"),
        ("new-project-title", getattr(project, "title", "") or ""),
    ]
    for el_id, value in composites:
        attrs = {"type": "hidden", "id": el_id, "value": value}
        hidden_inputs.append(el("input", **attrs))

    stored_sections = _composer_value(profile, "sections")
    if not stored_sections and topic is not None:
        stored_sections = list(topic.structure_sections)
    stages = _composer_value(profile, "stages")
    stages_json = json.dumps(stages) if stages else ""

    current_assets = {}
    for role, pkey in (
        ("bg_clip", "asset_bg_clip_id"),
        ("music", "asset_music_id"),
        ("outro_clip", "asset_outro_clip_id"),
        ("font", "asset_font_id"),
        ("watermark", "asset_watermark_id"),
    ):
        value = _composer_value(profile, pkey)
        if value:
            current_assets[role] = value
    for role, url_key in (
        ("bg_clip", "media_url_bg_clip"),
        ("music", "media_url_music"),
        ("outro_clip", "media_url_outro"),
        ("watermark", "media_url_watermark"),
    ):
        value = _composer_value(profile, url_key)
        if value:
            current_assets[f"{role}_url"] = value
    if _composer_value(profile, "bg_source") == "api":
        current_assets["bg_clip_source"] = "api"
        current_assets["bg_clip_provider"] = _composer_value(profile, "stock_provider") or "auto"

    return el(
        "div",
        el(
            "form",
            *hidden_inputs,
            el("div", id="project-settings-feedback", class_="mb-4"),
            el(
                "div",
                _wizard_format_field(profile),
                _wizard_duration_field(profile),
                el("div", _wizard_caption_field(profile), id="new-project-caption-field"),
                class_="mb-6",
            ),
            el(
                "div",
                _presets_panel(),
                _content_panel(profile),
                _style_panel(profile),
                _placement_panel(profile),
                _phase2_panel(profile, builtin_profile),
                _media_panel(
                    asset_options or {},
                    current=current_assets,
                    stages_json=stages_json,
                    stock_providers=stock_providers,
                    format_name=profile.format_name.value if profile.format_name else None,
                    bg_mode=_composer_value(profile, "bg_mode") or "",
                ),
                _spec_panel(),
                id="composer-panels",
                class_="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4",
            ),
            Markup(preview_styles),
            Markup(composer_preview_js()),
            _wizard_globals_js(active_classes, compatible_formats_by_topic()),
            id="project-profile-form",
            method="post",
            action=f"/api/projects/{project.id}/settings",
            hx_post=f"/api/projects/{project.id}/settings",
            hx_target="#project-settings-feedback",
            hx_swap="innerHTML",
            hx_indicator="#profile-save-indicator",
            data_dirty="false",
            class_="md:col-span-2",
        ),
        el(
            "div",
            Markup(_preview_phone(active_classes)),
            el(
                "div",
                _profile_strip(
                    profile,
                    reset_url=f"/api/projects/{project.id}/reset-override",
                ),
                el(
                    "span",
                    "Saving\u2026",
                    id="profile-save-indicator",
                    class_="htmx-indicator text-xs text-primary",
                ),
                ActionButton(
                    "Save Settings",
                    size="lg",
                    type="submit",
                    id="profile-save-btn",
                    form="project-profile-form",
                    class_extra="w-full",
                ),
                class_="space-y-3",
            ),
            class_="md:col-span-1 space-y-6 md:sticky md:top-6 md:self-start",
        ),
        class_="grid grid-cols-1 md:grid-cols-3 gap-6",
    )
