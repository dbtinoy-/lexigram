from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.ui.components.settings_profile import (
    profile_error_slot,
    profile_field,
    profile_summary,
    source_badge,
)
from shorts_creator.ui.pages.new_project import project_settings_form


def _resolved(value, source):
    return ResolvedSetting(
        value=value, source=source, is_overridden=source is ProfileSource.PROJECT
    )


def settings_profile(**kwargs) -> EffectiveProjectProfile:
    data = {
        "topic": _resolved("self_improvement", ProfileSource.GLOBAL),
        "format_name": _resolved("narrated", ProfileSource.BUILT_IN),
        "duration_seconds": _resolved(30, ProfileSource.GLOBAL),
        "caption_style": _resolved("highlight", ProfileSource.BUILT_IN),
        "asset_music_id": _resolved(None, ProfileSource.BUILT_IN),
        "asset_font_id": _resolved(None, ProfileSource.BUILT_IN),
        "asset_bg_clip_id": _resolved(None, ProfileSource.BUILT_IN),
        "asset_outro_clip_id": _resolved(None, ProfileSource.BUILT_IN),
        "asset_watermark_id": _resolved(None, ProfileSource.BUILT_IN),
        "media_url_music": _resolved(None, ProfileSource.BUILT_IN),
        "media_url_bg_clip": _resolved(None, ProfileSource.BUILT_IN),
        "media_url_outro": _resolved(None, ProfileSource.BUILT_IN),
        "media_url_watermark": _resolved(None, ProfileSource.BUILT_IN),
    }
    data.update(kwargs)
    return EffectiveProjectProfile(**data)


def _setting(value, source, is_overridden=None):
    if is_overridden is None:
        is_overridden = source is ProfileSource.PROJECT
    return ResolvedSetting(value=value, source=source, is_overridden=is_overridden)


def _project(project_id="p1"):
    class _Project:
        id = project_id
        title = "My Short"

    return _Project()


ASSET_OPTIONS = {
    "music": [("m1", "Lo-fi")],
    "font": [("f1", "Inter")],
    "bg_clip": [("bg1", "City")],
    "outro_clip": [("o1", "Outro")],
    "watermark": [("w1", "Mark")],
}


def _settings_html(profile=None, asset_options=None, project_id="p1"):
    return str(
        project_settings_form(
            _project(project_id),
            profile or settings_profile(),
            asset_options or ASSET_OPTIONS,
        )
    )


class TestProfileField:
    def test_profile_field_shows_effective_value_source_and_reset(self):
        html = profile_field(
            key="duration_seconds",
            label="Duration",
            setting=_setting(45, ProfileSource.PROJECT, is_overridden=True),
            input_html='<input name="duration_seconds">',
        )
        assert "Duration" in html
        assert 'name="duration_seconds"' in html
        assert "Project override" in html
        assert "Reset" in html
        assert 'data-profile-field="duration_seconds"' in html
        assert "data-override-toggle" in html

    def test_profile_field_inherited_setting_has_no_reset(self):
        html = profile_field(
            key="duration_seconds",
            label="Duration",
            setting=_setting(30, ProfileSource.GLOBAL),
            input_html='<input name="duration_seconds">',
        )
        assert "Global Default" in html
        assert "Reset" not in html

    def test_profile_field_help_text_rendered(self):
        html = profile_field(
            key="duration_seconds",
            label="Duration",
            setting=_setting(45, ProfileSource.PROJECT),
            input_html="<input>",
            help_text="Seconds per short",
        )
        assert "Seconds per short" in html


class TestProfileSummary:
    def test_profile_summary_counts_inherited_and_customized_fields(self):
        profile = settings_profile(
            duration_seconds=_setting(45, ProfileSource.PROJECT),
            format_name=_setting("narrated", ProfileSource.PROJECT),
            caption_style=_setting("highlight", ProfileSource.GLOBAL),
        )
        html = profile_summary(profile)
        assert "Customized: 2" in html
        assert "Inherited: 1" in html

    def test_profile_summary_only_project_is_customized(self):
        profile = settings_profile(
            duration_seconds=_setting(45, ProfileSource.PROJECT),
            caption_style=_setting("highlight", ProfileSource.GLOBAL),
            asset_music_id=_setting("m1", ProfileSource.GLOBAL),
        )
        html = profile_summary(profile)
        assert "Customized: 1" in html
        assert "Inherited: 3" in html


class TestSourceBadge:
    def test_source_badge_labels_each_source(self):
        assert "Project override" in source_badge(_setting("x", ProfileSource.PROJECT))
        assert "Global Default" in source_badge(_setting("x", ProfileSource.GLOBAL))
        assert "Format" in source_badge(_setting("x", ProfileSource.FORMAT))
        assert "Built-in" in source_badge(_setting("x", ProfileSource.BUILT_IN))

    def test_source_badge_carries_data_source(self):
        html = source_badge(_setting("x", ProfileSource.PROJECT))
        assert 'data-source="project"' in html


class TestProjectSettingsForm:
    def test_form_targets_feedback_container(self):
        html = _settings_html()
        assert 'id="project-profile-form"' in html
        assert 'action="/api/projects/p1/settings"' in html
        assert 'hx-post="/api/projects/p1/settings"' in html
        assert 'hx-target="#project-settings-feedback"' in html
        assert 'hx-indicator="#profile-save-indicator"' in html

    def test_save_bar_has_button_and_indicator(self):
        html = _settings_html()
        assert "Save Settings" in html
        assert 'id="profile-save-btn"' in html
        assert 'id="profile-save-indicator"' in html

    def test_hidden_inputs_carry_no_name(self):
        html = _settings_html()
        assert 'type="hidden"' in html
        assert 'name="new-project-title"' not in html
        assert 'name="new-project-type"' not in html
        assert 'name="new-project-format"' not in html

    def test_media_pickers_rendered(self):
        html = _settings_html()
        assert 'name="asset_music_id"' in html
        assert 'name="asset_font_id"' in html
        assert 'name="asset_bg_clip_id"' in html
        assert 'name="asset_outro_clip_id"' in html
        assert 'name="asset_watermark_id"' in html
        assert 'name="media_url_music"' in html
        assert 'name="media_source_bg_clip"' in html
        assert 'name="stock_provider_bg_clip"' in html

    def test_auto_default_option_not_inherit_text(self):
        html = _settings_html()
        assert "Auto (default)" in html
        assert "Inherit (global default)" not in html

    def test_selected_asset_is_marked(self):
        html = _settings_html(settings_profile(asset_music_id=_setting("m1", ProfileSource.GLOBAL)))
        assert ">Lo-fi</option>" in html
        assert 'value="m1" selected' in html

    def test_profile_summary_present(self):
        html = _settings_html()
        assert 'id="profile-summary"' in html

    def test_no_legacy_profile_editor_js(self):
        html = _settings_html()
        assert "profile-editor.js" not in html


class TestProfileErrorWiring:
    def test_field_renders_per_field_error_slot(self):
        html = profile_field(
            key="duration_seconds",
            label="Duration",
            setting=_setting(45, ProfileSource.PROJECT, is_overridden=True),
            input_html="<input>",
        )
        assert 'id="profile-field-error-duration_seconds"' in html
        assert "profile-error-slot" in html

    def test_error_slot_targets_field_inline(self):
        slot = profile_error_slot("duration_seconds", "must be greater than zero")
        assert 'id="profile-field-error-duration_seconds"' in slot
        assert 'hx-swap-oob="innerHTML:#profile-field-error-duration_seconds"' in slot
        assert "must be greater than zero" in slot
