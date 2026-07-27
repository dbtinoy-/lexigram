import json

from shorts_creator.controllers.project_settings import ProjectSettingsController
from shorts_creator.models.asset import Asset
from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.services.asset_service import AssetService
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_service import ProjectService


class FakeRepo:
    def __init__(self):
        self.store: dict[str, Project] = {}

    async def create(self, project):
        self.store[project.id] = project
        return project

    async def update(self, project):
        self.store[project.id] = project
        return project

    async def get(self, project_id):
        return self.store.get(project_id)

    async def list_recent(self, limit=50):
        return list(self.store.values())[:limit]


class FakeJsonRequest:
    def __init__(self, payload: dict):
        self._payload = payload

    async def json(self):
        return self._payload

    async def form(self):
        raise TypeError("no form body")


class FakeFormRequest:
    def __init__(self, payload: dict):
        self._payload = payload

    async def json(self):
        raise TypeError("no json body")

    async def form(self):
        return self._payload


class FakeAssetService:
    def __init__(self, assets: list[Asset]):
        self._assets = assets

    async def list_by_type(self, asset_type, role=None):
        return [a for a in self._assets if a.type == asset_type and a.role == role]


def _setting(value, source: ProfileSource) -> ResolvedSetting:
    return ResolvedSetting(
        value=value, source=source, is_overridden=source is ProfileSource.PROJECT
    )


class FakeProfileService:
    """Resolved effective profile the save endpoint compares form values
    against via form_overrides()' inherited-default check."""

    def __init__(self, profile: EffectiveProjectProfile):
        self._profile = profile

    async def resolve(self, project):
        return self._profile

    @staticmethod
    def validate(profile):
        return {}

    async def validate_pair_for_project(self, project):
        return []


class _OverrideAwareFakeProfileService:
    """Resolves the effective profile with the project's overrides, or a
    bare profile when the overrides are suppressed (built-in pass)."""

    def __init__(self, with_overrides: EffectiveProjectProfile, bare: EffectiveProjectProfile):
        self._with_overrides = with_overrides
        self._bare = bare

    async def resolve(self, project):
        overrides = json.loads(project.profile_overrides_json or "{}")
        return self._with_overrides if overrides else self._bare

    @staticmethod
    def validate(profile):
        return {}

    async def validate_pair_for_project(self, project):
        return []


def _profile(**fields) -> EffectiveProjectProfile:
    base = {
        "topic": _setting("self_improvement", ProfileSource.PROJECT),
        "duration_seconds": _setting(44.0, ProfileSource.FORMAT),
        "caption_style": _setting("highlight", ProfileSource.GLOBAL),
        "format_name": _setting("narrated", ProfileSource.FORMAT),
    }
    base.update(fields)
    return EffectiveProjectProfile(**base)


NARRATED_LAYOUT = {
    "anchor": "center",
    "block_width_pct": 80,
    "numbered_scale": 1.6,
    "pill_per_word": True,
}
NARRATED_STAGES = {"music": False, "outro": True, "watermark": False, "background": True}


async def _make_controller(profile=None, assets=None):
    if profile is None:
        profile = _profile()
    repo = FakeRepo()
    project = Project(topic="self_improvement", title="P")
    await repo.create(project)
    asset_service = FakeAssetService(assets or [])
    config = AppConfig.from_dict(
        {"reel_width": 1080, "reel_height": 1920, "default_duration": 30.0}
    )
    controller = ProjectSettingsController(
        config=config,
        projects=ProjectService(repo),
        store=None,
        asset_service=AssetService(asset_service),
        profile_service=FakeProfileService(profile),
    )
    controller.layout = _RawLayout()
    return controller, project.id


class _RawLayout:
    """Renders the settings page body verbatim so assertions target the
    composer panels rather than the surrounding shell."""

    def render(self, content="", title="", request=None):
        return content


def body_of(content) -> str:
    return content.body if hasattr(content, "body") else str(content)


class TestComposeSave:
    async def test_save_persists_composer_overrides(self):
        controller, pid = await _make_controller()
        resp = await controller.save_project_settings(
            request=FakeJsonRequest(
                {
                    "pacing_wps": "2.7",
                    "hook_text": "Wide hook",
                    "outro_text": "See you next time",
                    "sections": '["message"]',
                    "style": '{"chunk_size": 5, "uppercase": true, "scrim_alpha": 0.4}',
                    "palette": '{"highlight_colour": "0xFF00FFFF"}',
                    "layout": '{"anchor": "lower_third", "block_width_pct": 70, "watermark_corner": "top_left", "music_volume": 0.3}',
                    "stages": '{"music": true}',
                }
            ),
            id=pid,
        )
        assert "Profile saved" in body_of(resp)
        row = await controller.projects.repo.get(pid)
        saved = json.loads(row.profile_overrides_json)
        assert saved["pacing_wps"] == 2.7
        assert saved["hook_text"] == "Wide hook"
        assert saved["outro_text"] == "See you next time"
        assert saved["sections"] == ["message"]
        assert saved["style"] == {"chunk_size": 5, "uppercase": True, "scrim_alpha": 0.4}
        assert saved["palette"] == {"highlight_colour": "0xFF00FFFF"}
        assert saved["layout"] == {
            "anchor": "lower_third",
            "block_width_pct": 70,
            "watermark_corner": "top_left",
            "music_volume": 0.3,
        }
        assert saved["stages"] == {"music": True}

    async def test_save_skips_values_equal_to_inherited(self):
        controller, pid = await _make_controller(
            _profile(
                layout=_setting(dict(NARRATED_LAYOUT), ProfileSource.FORMAT),
                stages=_setting(dict(NARRATED_STAGES), ProfileSource.FORMAT),
                asset_music_id=_setting("m-1", ProfileSource.GLOBAL),
            )
        )
        resp = await controller.save_project_settings(
            request=FakeJsonRequest(
                {
                    "layout": '{"anchor": "center", "block_width_pct": 80, "numbered_scale": 1.6, "pill_per_word": true}',
                    "stages": '{"music": false, "outro": true, "watermark": false, "background": true}',
                    "asset_music_id": "m-1",
                }
            ),
            id=pid,
        )
        assert "Profile saved" in body_of(resp)
        row = await controller.projects.repo.get(pid)
        saved = json.loads(row.profile_overrides_json or "{}")
        assert saved == {}

    async def test_save_persists_value_diverging_from_inherited(self):
        controller, pid = await _make_controller(
            _profile(
                layout=_setting(dict(NARRATED_LAYOUT), ProfileSource.FORMAT),
                asset_music_id=_setting("m-1", ProfileSource.GLOBAL),
            )
        )
        await controller.save_project_settings(
            request=FakeJsonRequest(
                {
                    "layout": '{"anchor": "lower_third", "block_width_pct": 80, "numbered_scale": 1.6, "pill_per_word": true}',
                    "asset_music_id": "m-2",
                }
            ),
            id=pid,
        )
        row = await controller.projects.repo.get(pid)
        saved = json.loads(row.profile_overrides_json)
        assert saved["layout"] == {
            "anchor": "lower_third",
            "block_width_pct": 80,
            "numbered_scale": 1.6,
            "pill_per_word": True,
        }
        assert saved["asset_music_id"] == "m-2"

    async def test_save_rejects_invalid_values(self):
        controller, pid = await _make_controller()
        resp = await controller.save_project_settings(
            request=FakeJsonRequest({"layout": '{"anchor": "upper_third"}'}),
            id=pid,
        )
        assert "fix the values" in body_of(resp)
        assert "anchor must be center or lower_third" in body_of(resp)
        row = await controller.projects.repo.get(pid)
        assert json.loads(row.profile_overrides_json or "{}") == {}

    async def test_save_unknown_project_404(self):
        controller, _ = await _make_controller()
        resp = await controller.save_project_settings(request=None, id="missing")
        assert resp.status_code == 404


class TestFormOverridesAssetProvenance:
    async def test_asset_equal_to_inherited_is_skipped(self):
        from shorts_creator.ui.pages.new_project import form_overrides

        profile = _profile(asset_music_id=_setting("m-1", ProfileSource.GLOBAL))
        overrides = form_overrides({"asset_music_id": "m-1", "asset_font_id": ""}, profile)
        assert overrides == {}

    async def test_media_url_set_is_persisted(self):
        from shorts_creator.ui.pages.new_project import form_overrides

        overrides = form_overrides({"media_url_music": "https://cdn.example/track.mp3"}, None)
        assert overrides == {"media_url_music": "https://cdn.example/track.mp3"}

    async def test_media_url_cleared_wins_over_inherited(self):
        from shorts_creator.ui.pages.new_project import form_overrides

        profile = _profile(
            media_url_music=_setting("https://cdn.example/track.mp3", ProfileSource.GLOBAL)
        )
        overrides = form_overrides(
            {"media_url_music": "", "media_url_bg_clip": "https://x/b.mp4"}, profile
        )
        assert overrides == {"media_url_music": "", "media_url_bg_clip": "https://x/b.mp4"}

    async def test_media_url_absent_is_not_cleared(self):
        from shorts_creator.ui.pages.new_project import form_overrides

        profile = _profile(
            media_url_music=_setting("https://cdn.example/track.mp3", ProfileSource.GLOBAL)
        )
        overrides = form_overrides({"asset_font_id": "f-1"}, profile)
        assert overrides == {"asset_font_id": "f-1"}

    async def test_outro_text_persisted_only_when_non_empty(self):
        from shorts_creator.ui.pages.new_project import form_overrides

        overrides = form_overrides({"outro_text": "Keep going"}, None)
        assert overrides == {"outro_text": "Keep going"}
        overrides = form_overrides({"outro_text": "   "}, None)
        assert overrides == {}
        overrides = form_overrides({"outro_text": ""}, None)
        assert overrides == {}

    async def test_api_source_persists_provider(self):
        from shorts_creator.ui.pages.new_project import form_overrides

        overrides = form_overrides(
            {"media_source_bg_clip": "api", "stock_provider_bg_clip": "pexels"}, None
        )
        assert overrides == {"bg_source": "api", "stock_provider": "pexels"}

    async def test_api_source_defaults_provider_to_auto(self):
        from shorts_creator.ui.pages.new_project import form_overrides

        overrides = form_overrides({"media_source_bg_clip": "api"}, None)
        assert overrides == {"bg_source": "api", "stock_provider": "auto"}

    async def test_leaving_api_source_clears_it(self):
        from shorts_creator.ui.pages.new_project import form_overrides

        profile = _profile(bg_source=_setting("api", ProfileSource.PROJECT))
        overrides = form_overrides({"media_source_bg_clip": "assets"}, profile)
        assert overrides == {"bg_source": "", "stock_provider": "", "media_url_bg_clip": ""}

    async def test_absent_source_select_does_not_touch_api_fields(self):
        from shorts_creator.ui.pages.new_project import form_overrides

        profile = _profile(bg_source=_setting("api", ProfileSource.PROJECT))
        overrides = form_overrides({}, profile)
        assert overrides == {}


class TestComposePage:
    async def test_page_prefills_resolved_overrides(self):
        controller, pid = await _make_controller(
            _profile(
                pacing_wps=_setting(2.7, ProfileSource.PROJECT),
                hook_text=_setting("Wide hook", ProfileSource.PROJECT),
                outro_text=_setting("Keep going", ProfileSource.PROJECT),
                sections=_setting(["message", "metaphor"], ProfileSource.PROJECT),
                style=_setting(
                    {"chunk_size": 5, "uppercase": True, "scrim_alpha": 0.4}, ProfileSource.PROJECT
                ),
                palette=_setting({"highlight_colour": "0xFF00FFFF"}, ProfileSource.PROJECT),
                layout=_setting(
                    {
                        "anchor": "lower_third",
                        "block_width_pct": 70,
                        "watermark_corner": "top_left",
                        "watermark_size_pct": 20,
                        "watermark_opacity": 0.5,
                        "music_volume": 0.3,
                        "music_fade_seconds": 4.0,
                        "fade_out_seconds": 2.0,
                    },
                    ProfileSource.PROJECT,
                ),
                stages=_setting(
                    {"music": True, "outro": True, "watermark": False, "background": False},
                    ProfileSource.PROJECT,
                ),
                asset_music_id=_setting("m-1", ProfileSource.PROJECT),
            ),
            assets=[
                Asset(id="m-1", type="music", name="Night Drive"),
                Asset(id="m-2", type="music", name="Sunset"),
            ],
        )
        resp = await controller.project_settings(request=None, id=pid)
        body = body_of(resp)
        assert 'id="project-profile-form"' in body
        assert 'id="composer-panels"' in body
        assert 'value="2.7"' in body
        assert 'value="Wide hook"' in body
        assert 'value="Keep going"' in body
        assert 'name="sections"' in body
        assert "message" in body and "metaphor" in body
        assert 'value="5"' in body
        assert 'value="#ff00ff"' in body
        assert 'id="new-project-uppercase"' in body
        assert 'value="0.4"' in body
        assert 'id="new-project-watermark-corner"' in body
        assert '<option value="top_left" selected>' in body
        assert 'value="20"' in body
        assert 'value="0.5"' in body
        assert 'value="0.3"' in body
        assert 'value="4"' in body
        assert 'value="2"' in body
        assert (
            'data-anchor="lower_third" class="anchor-btn px-3 py-1.5 text-xs rounded-lg cursor-pointer transition-colors bg-primary'
            in body
        )
        assert "data-stages=" in body
        assert '<option value="m-1" selected>' in body
        assert 'value="70"' in body

    async def test_page_defaults_when_no_overrides(self):
        controller, pid = await _make_controller()
        resp = await controller.project_settings(request=None, id=pid)
        body = body_of(resp)
        assert 'value="2.5"' in body
        assert "data-stages=" not in body
        assert '<option value="m-1"' not in body
        assert (
            'data-anchor="center" class="anchor-btn px-3 py-1.5 text-xs rounded-lg cursor-pointer transition-colors bg-primary'
            in body
        )
        assert 'value="#7c5cfa"' in body


class TestComposePageBuiltinKnobDefaults:
    """Gap E1: the settings page ships data_builtin from a second resolution
    pass with the project's overrides suppressed."""

    @staticmethod
    def _controller_with(projects, profile_service, assets=None):
        config = AppConfig.from_dict(
            {"reel_width": 1080, "reel_height": 1920, "default_duration": 30.0}
        )
        controller = ProjectSettingsController(
            config=config,
            projects=projects,
            store=None,
            asset_service=AssetService(FakeAssetService(assets or [])),
            profile_service=profile_service,
        )
        controller.layout = _RawLayout()
        return controller

    def _make(self, with_overrides, bare, overrides_json):
        repo = FakeRepo()
        project = Project(
            topic="self_improvement",
            title="P",
            profile_overrides_json=overrides_json if overrides_json else "{}",
        )
        projects = ProjectService(repo)
        return (
            self._controller_with(
                projects,
                _OverrideAwareFakeProfileService(with_overrides, bare),
            ),
            projects,
            project,
        )

    async def test_page_knobs_carry_overrides_suppressed_builtin(self):
        controller, projects, project = self._make(
            _profile(section_holds=_setting({"message": 1.5}, ProfileSource.PROJECT)),
            _profile(section_holds=_setting({}, ProfileSource.BUILT_IN)),
            '{"section_holds": {"message": 1.5}}',
        )
        await projects.repo.create(project)
        resp = await controller.project_settings(request=None, id=project.id)
        body = body_of(resp)
        row = body.split('id="new-project-message-pacing"')[1].split(">")[0]
        assert 'data-default="2.5"' in row
        assert 'data-builtin="1"' in row

    async def test_page_neutral_knob_builtin_matches_default(self):
        controller, projects, project = self._make(_profile(), _profile(), "")
        await projects.repo.create(project)
        resp = await controller.project_settings(request=None, id=project.id)
        body = body_of(resp)
        for widget_id in (
            "new-project-hold-hook",
            "new-project-message-pacing",
            "new-project-hold-conclusion",
        ):
            row = body.split(f'id="{widget_id}"')[1].split(">")[0]
            default = row.split('data-default="')[1].split('"')[0]
            assert f'data-builtin="{default}"' in row


class TestMediaPanelStockApi:
    def test_panel_offers_api_source_with_configured_providers(self):
        from shorts_creator.ui.pages.new_project import _media_panel

        html = str(_media_panel({}, stock_providers=["pexels", "pixabay"]))
        assert "Stock clip" in html
        assert 'name="stock_provider_bg_clip"' in html
        assert '<option value="auto"' in html
        assert "Pexels" in html and "Pixabay" in html
        assert 'name="stock_provider_music"' not in html

    def test_panel_preselects_api_source_and_provider_in_edit_mode(self):
        from shorts_creator.ui.pages.new_project import _media_panel

        html = str(
            _media_panel(
                {},
                current={"bg_clip_source": "api", "bg_clip_provider": "pixabay"},
                stock_providers=["pexels", "pixabay"],
            )
        )
        assert '<option value="api" selected>' in html
        assert '<option value="pixabay" selected>' in html

    def test_panel_omits_api_option_when_no_providers_configured(self):
        from shorts_creator.ui.pages.new_project import _media_panel

        html = str(_media_panel({}, stock_providers=[]))
        assert "Stock clip" in html
        assert 'name="stock_provider_bg_clip"' in html
        assert "Pexels" not in html

    async def test_page_save_roundtrip_via_form(self):
        controller, pid = await _make_controller()
        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "pacing_wps": "2.1",
                    "outro_text": "Round trip outro",
                    "sections": '["message"]',
                    "layout": '{"anchor": "lower_third"}',
                    "stages": '{"music": true, "outro": true, "watermark": false, "background": true}',
                }
            ),
            id=pid,
        )
        assert "Profile saved" in body_of(resp)
        row = await controller.projects.repo.get(pid)
        saved = json.loads(row.profile_overrides_json)
        assert saved["pacing_wps"] == 2.1
        assert saved["outro_text"] == "Round trip outro"
        assert saved["sections"] == ["message"]
        assert saved["layout"] == {"anchor": "lower_third"}
        assert saved["stages"] == {
            "music": True,
            "outro": True,
            "watermark": False,
            "background": True,
        }

    async def test_page_unknown_project_404(self):
        controller, _ = await _make_controller()
        resp = await controller.project_settings(request=None, id="missing")
        assert resp.status_code == 404


class TestPhase2Knobs:
    async def test_save_persists_phase2_overrides(self):
        controller, pid = await _make_controller()
        resp = await controller.save_project_settings(
            request=FakeJsonRequest(
                {
                    "background_motion": "zoom",
                    "emphasis_style": "off",
                    "loudness_target_lufs": "-16",
                    "audio_normalize": "false",
                    "section_holds": '{"hook": 0.4, "message": 0.8, "conclusion": 0.3}',
                    "stage_accents": '{"message": "0xFF00FFFF"}',
                }
            ),
            id=pid,
        )
        assert "Profile saved" in body_of(resp)
        row = await controller.projects.repo.get(pid)
        saved = json.loads(row.profile_overrides_json)
        assert saved["background_motion"] == "zoom"
        assert saved["emphasis_style"] == "off"
        assert saved["loudness_target_lufs"] == -16.0
        assert saved["audio_normalize"] is False
        assert saved["section_holds"] == {"hook": 0.4, "message": 0.8, "conclusion": 0.3}
        assert saved["stage_accents"] == {"message": "0xFF00FFFF"}

    async def test_save_skips_phase2_neutral_values(self):
        controller, pid = await _make_controller()
        resp = await controller.save_project_settings(
            request=FakeJsonRequest(
                {
                    "background_motion": "none",
                    "emphasis_style": "accent",
                    "loudness_target_lufs": "-14",
                    "audio_normalize": "true",
                    "section_holds": "",
                    "stage_accents": "",
                }
            ),
            id=pid,
        )
        assert "Profile saved" in body_of(resp)
        row = await controller.projects.repo.get(pid)
        assert json.loads(row.profile_overrides_json or "{}") == {}

    async def test_save_ignores_malformed_phase2_values(self):
        controller, pid = await _make_controller()
        resp = await controller.save_project_settings(
            request=FakeJsonRequest(
                {
                    "loudness_target_lufs": "loud",
                    "section_holds": "not-json",
                    "stage_accents": "not-json",
                }
            ),
            id=pid,
        )
        assert "Profile saved" in body_of(resp)
        row = await controller.projects.repo.get(pid)
        assert json.loads(row.profile_overrides_json or "{}") == {}

    async def test_save_phase2_form_roundtrip(self):
        controller, pid = await _make_controller()
        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "background_motion": "zoom",
                    "audio_normalize": "false",
                    "section_holds": '{"message": 1.2}',
                    "stage_accents": '{"metaphor": "0x22D3EEFF"}',
                }
            ),
            id=pid,
        )
        assert "Profile saved" in body_of(resp)
        row = await controller.projects.repo.get(pid)
        saved = json.loads(row.profile_overrides_json)
        assert saved["background_motion"] == "zoom"
        assert saved["audio_normalize"] is False
        assert saved["section_holds"] == {"message": 1.2}
        assert saved["stage_accents"] == {"metaphor": "0x22D3EEFF"}

    async def test_page_prefills_phase2_knobs(self):
        controller, pid = await _make_controller(
            _profile(
                background_motion=_setting("zoom", ProfileSource.PROJECT),
                emphasis_style=_setting("off", ProfileSource.PROJECT),
                loudness_target_lufs=_setting(-16.0, ProfileSource.PROJECT),
                audio_normalize=_setting(False, ProfileSource.PROJECT),
                section_holds=_setting(
                    {"hook": 0.5, "message": 0.8, "conclusion": 0.25}, ProfileSource.PROJECT
                ),
                stage_accents=_setting({"message": "0x22D3EEFF"}, ProfileSource.PROJECT),
            ),
        )
        resp = await controller.project_settings(request=None, id=pid)
        body = body_of(resp)
        assert 'id="new-project-motion"' in body
        assert (
            'data-motion="zoom" class="motion-btn px-3 py-1.5 text-xs rounded-lg cursor-pointer transition-colors bg-primary'
            in body
        )
        assert 'id="new-project-emphasis"' in body
        assert (
            'data-emphasis="off" class="emphasis-btn px-3 py-1.5 text-xs rounded-lg cursor-pointer transition-colors bg-primary'
            in body
        )
        assert 'id="new-project-hold-hook"' in body and 'value="0.5"' in body
        assert (
            'id="new-project-message-pacing" type="range" min="0.5" max="3" step="0.1" value="1.8"'
            in body
        )
        assert 'id="new-project-hold-conclusion"' in body and 'value="0.25"' in body
        assert (
            'id="new-project-loudness" type="number" min="-20" max="-8" step="0.5" value="-16"'
            in body
        )
        assert 'id="new-project-audio-normalize" type="checkbox"' in body
        assert 'id="new-project-hold-hook-readout"' in body
        assert 'data-default="0.5"' in body
        assert 'data-accent="cyan" data-colour="0x22D3EEFF"' in body
        msg_block = body.split('id="new-project-stage-accent-message"')[1]
        assert 'data-colour="0x22D3EEFF"' in msg_block
        assert "ring-primary" in msg_block
        assert 'name="section_holds"' in body
        assert 'name="stage_accents"' in body
        assert 'name="background_motion"' in body

    async def test_page_defaults_phase2_when_no_overrides(self):
        controller, pid = await _make_controller()
        resp = await controller.project_settings(request=None, id=pid)
        body = body_of(resp)
        assert 'id="new-project-motion"' in body
        assert (
            'data-motion="none" class="motion-btn px-3 py-1.5 text-xs rounded-lg cursor-pointer transition-colors bg-primary'
            in body
        )
        assert (
            'data-emphasis="accent" class="emphasis-btn px-3 py-1.5 text-xs rounded-lg cursor-pointer transition-colors bg-primary'
            in body
        )
        assert (
            'id="new-project-message-pacing" type="range" min="0.5" max="3" step="0.1" value="1"'
            in body
        )
        assert (
            'id="new-project-hold-hook" type="range" min="0" max="1" step="0.1" value="0"' in body
        )
        assert (
            'id="new-project-loudness" type="number" min="-20" max="-8" step="0.5" value="-14"'
            in body
        )
        assert 'id="new-project-stage-accent-hook"' in body
        assert 'data-accent="violet" data-colour="0x7C5CFAFF"' in body
        assert 'data-default="-14"' in body

    async def test_page_renders_phase2_panel_on_create_page(self):
        from shorts_creator.ui.pages.new_project import new_project_form

        html = str(new_project_form())
        assert "composer-phase2-panel" in html
        assert 'id="new-project-stage-accent-conclusion"' in html
        assert 'id="new-project-audio-normalize-json" type="hidden" name="audio_normalize"' in html


class TestComposerPreviewRanges:
    def test_preview_json_exposes_duration_and_pacing_ranges(self):
        from shorts_creator.ui.pages.new_project import _composer_preview_json

        formats = _composer_preview_json()["formats"]
        assert formats["narrated"]["label"] == "Narrated"
        assert formats["narrated"]["duration_range"] == [38, 50]
        assert formats["narrated"]["pacing_wps_range"] == [2.5, 3.0]
        assert "steps" in formats
        assert "myth" in formats

    def test_topn_exposes_its_own_declared_ranges(self):
        from shorts_creator.ui.pages.new_project import _composer_preview_json

        formats = _composer_preview_json()["formats"]
        assert formats["topn"]["duration_range"] == [35, 50]
        assert formats["topn"]["pacing_wps_range"] == [2.4, 3.0]
