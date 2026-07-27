import json
from pathlib import Path

import pytest

from shorts_creator.controllers.projects import ProjectsController
from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.services.project_service import ProjectService

STATIC_JS = Path(__file__).resolve().parents[1] / "src/shorts_creator/ui/static/js"
PREVIEW_JS = (STATIC_JS / "composer-preview.js").read_text()
FORM_JS = (STATIC_JS / "project-form.js").read_text()


def _preview_data_blob(body) -> dict:
    return json.loads(body.split("__PREVIEW_JSON__ = ")[1].split(";")[0])


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


class FakeFormRequest:
    def __init__(self, form_data: dict[str, str]):
        self._form_data = form_data

    async def form(self):
        return self._form_data

    async def json(self):
        raise TypeError("no json body")


@pytest.fixture
def projects():
    return ProjectService(FakeRepo())


@pytest.fixture
async def controller(projects):
    return ProjectsController(projects=projects)


def body_of(content) -> str:
    return content.body if hasattr(content, "body") else str(content)


def _setting(value, source: ProfileSource) -> ResolvedSetting:
    return ResolvedSetting(
        value=value, source=source, is_overridden=source is ProfileSource.PROJECT
    )


class FakeProfileService:
    """Stub of ProjectProfileService.resolve: format duration midpoint,
    built-in defaults, and a global-tier caption like the real resolver."""

    def __init__(
        self,
        duration: float = 44.0,
        caption_style: str = "highlight",
    ):
        self.duration = duration
        self.caption_style = caption_style

    async def resolve(self, project):
        return EffectiveProjectProfile(
            duration_seconds=_setting(self.duration, ProfileSource.FORMAT),
            caption_style=_setting(self.caption_style, ProfileSource.GLOBAL),
            format_name=_setting("narrated", ProfileSource.BUILT_IN),
            topic=_setting("self_improvement", ProfileSource.PROJECT),
            reel_width=_setting(1080, ProfileSource.BUILT_IN),
            reel_height=_setting(1920, ProfileSource.BUILT_IN),
        )


class TestSingleFormPage:
    async def test_new_project_page_has_no_wizard_and_single_form(self, controller):
        body = body_of(await controller.new_project_page())
        assert "guidedGo" not in body
        assert "create-step-" not in body
        assert "create-nav-" not in body
        assert body.count('<form id="create-project-form"') == 1
        assert 'hx-post="/api/projects/upsert"' in body

    async def test_single_form_contains_all_fields_once(self, controller):
        body = body_of(await controller.new_project_page())
        for name in ("title", "topic", "focus", "format", "caption_style", "duration_seconds"):
            assert body.count(f'name="{name}"') == 1

    async def test_layout_form_left_preview_and_button_right(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'class="grid grid-cols-1 md:grid-cols-3 gap-6"' in body
        form = body.split('<form id="create-project-form"')[1].split(">")[0]
        assert "md:col-span-2" in form
        assert "rounded-2xl" not in form
        assert "bg-card/40" not in form
        assert "border-border/60" not in form
        assert 'class="md:col-span-2"' in body
        assert 'id="new-project-preview-phone"' in body

    async def test_right_column_holds_only_preview_and_button(self, controller):
        body = body_of(await controller.new_project_page())
        assert body.index('id="new-project-preview-phone"') < body.index(
            'form="create-project-form"'
        )
        assert body.index('id="preview-skeleton-topn"') < body.index(
            'id="new-project-preview-phone"'
        )
        right = body.split('id="new-project-preview-phone"')[1]
        assert 'id="preview-skeleton-topn"' not in right

    async def test_details_pane_has_story_skeletons_and_profile(self, controller):
        body = body_of(await controller.new_project_page())
        details = body.split('id="create-wizard-tab"')[1].split('id="create-tabs"')[0]
        assert 'id="preview-skeleton-topn"' in details
        assert 'id="preview-skeleton-narrated"' in details
        assert "Effective profile" in details

    async def test_profile_summary_strip_keeps_sources(self, projects):
        controller = ProjectsController(
            projects=projects, profile_service=FakeProfileService(duration=60.0)
        )
        body = body_of(await controller.new_project_page())
        assert 'id="profile-summary"' in body
        assert "Customized" in body
        assert "Inherited" in body
        assert 'value="60"' in body
        assert "60s" in body
        assert "Skip any step" not in body
        assert "Create Project" in body

    async def test_form_prefills_resolved_caption_style(self, projects):
        controller = ProjectsController(
            projects=projects, profile_service=FakeProfileService(caption_style="plain")
        )
        body = body_of(await controller.new_project_page())
        assert '<option value="plain" selected>Plain (static lines)</option>' in body
        assert '<option value="highlight" selected>' not in body

    async def test_form_posts_to_feedback_target_and_keeps_error_slots(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'hx-target="#create-project-feedback"' in body
        assert 'id="profile-field-error-format_name"' in body
        assert 'id="profile-field-error-duration_seconds"' in body


class TestCreatePageTabs:
    async def test_form_fields_on_tab_and_knobs_on_composer_tab(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'id="create-tabs"' in body
        assert ">Form</button>" in body
        assert ">Composer</button>" in body
        assert "switchCreateTab(&#x27;form&#x27;)" in body
        assert "switchCreateTab(&#x27;composer&#x27;)" in body
        assert 'id="create-wizard-tab" data-create-tab="form" class="create-tab-panel">' in body
        assert (
            'id="composer-knobs-tab" data-create-tab="composer" class="create-tab-panel hidden">'
            in body
        )
        assert 'id="composer-panels"' in body

    async def test_composer_tab_active_classes_follow_switch(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'data-create-tab="form"' in body
        assert "text-primary border-primary bg-card/60" in body
        assert 'data-create-tab="composer"' in body
        assert (
            "text-muted-foreground border-transparent hover:text-foreground hover:border-border"
            in body
        )

    async def test_create_button_in_third_column_submits_external_form(self, controller):
        body = body_of(await controller.new_project_page())
        assert body.count('<form id="create-project-form"') == 1
        assert 'form="create-project-form"' in body
        assert 'class="md:col-span-1 space-y-6 md:sticky md:top-6 md:self-start"' in body
        assert body.index('form="create-project-form"') > body.index(
            'id="new-project-preview-phone"'
        )
        assert body.index("Create Project</span>") > body.index(">Story<")
        assert 'src="/static/js/project-form.js"' in body

    async def test_spec_panel_sits_right_of_media_panel(self, controller):
        body = body_of(await controller.new_project_page())
        panels = body.split('id="composer-panels"')[1].split('id="composer-knobs-tab"')[0]
        assert 'id="composer-media-panel-wrapper"' in panels
        assert 'id="composer-spec-panel"' in panels
        assert panels.index('id="composer-spec-panel"') > panels.index(
            'id="composer-media-panel-wrapper"'
        )
        assert 'id="composer-presets-panel"' in panels
        assert "md:col-span-2" in panels

    async def test_composer_panels_grid_spec_in_right_cell(self, controller):
        body = body_of(await controller.new_project_page())
        panels = body.split('id="composer-panels"')[1].split('id="composer-knobs-tab"')[0]
        assert 'class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4"' in body
        assert panels.rindex("</div>") > panels.index('id="composer-spec-panel"')

    async def test_third_column_markup_is_well_formed(self, controller):
        body = body_of(await controller.new_project_page())
        assert "<<div" not in body
        assert ' class="md:col-span-1"><button' not in body
        assert '</div><button type="submit" form="create-project-form"' in body
        assert "></<div" not in body


class TestCreateProjectProfile:
    async def test_create_project_persists_only_profile_overrides(self, controller, projects):
        await controller.upsert_project(
            FakeFormRequest(
                {
                    "title": "Morning Habits",
                    "topic": "self_improvement",
                    "format": "narrated",
                    "caption_style": "plain",
                    "duration_seconds": "45",
                }
            )
        )
        created = await projects.list_recent(1)
        overrides = json.loads(created[0].profile_overrides_json)
        assert overrides["duration_seconds"] == 45
        assert overrides["caption_style"] == "plain"

    async def test_create_untouched_form_prunes_values_equal_to_resolved_defaults(self, projects):
        controller = ProjectsController(
            projects=projects,
            profile_service=FakeProfileService(duration=44.0, caption_style="plain"),
        )
        await controller.upsert_project(
            FakeFormRequest(
                {
                    "title": "Untouched",
                    "topic": "self_improvement",
                    "format": "narrated",
                    "caption_style": "plain",
                    "duration_seconds": "44",
                }
            )
        )
        created = await projects.list_recent(1)
        assert created
        assert json.loads(created[0].profile_overrides_json) == {}

    async def test_create_without_optional_profile_fields_stores_empty_overrides(
        self, controller, projects
    ):
        await controller.upsert_project(
            FakeFormRequest(
                {
                    "title": "Minimal",
                    "topic": "self_improvement",
                }
            )
        )
        created = await projects.list_recent(1)
        assert created
        assert json.loads(created[0].profile_overrides_json) == {}
        assert created[0].title == "Minimal"

    async def test_create_redirects_to_project_page(self, controller, projects):
        response = await controller.upsert_project(
            FakeFormRequest(
                {
                    "title": "T",
                    "topic": "self_improvement",
                }
            )
        )
        created = await projects.list_recent(1)
        assert response.headers["HX-Redirect"] == f"/projects/{created[0].id}"

    async def test_create_rejects_invalid_profile_with_field_errors(self, controller, projects):
        response = await controller.upsert_project(
            FakeFormRequest(
                {
                    "title": "Bad",
                    "topic": "self_improvement",
                    "duration_seconds": "-5",
                }
            )
        )
        body = body_of(response)
        assert 'id="profile-field-error-duration_seconds"' in body
        assert "must be greater than zero" in body
        assert await projects.list_recent(1) == []


class TestPhonePreview:
    async def test_phone_preview_present_with_both_skeletons(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'id="new-project-preview-phone"' in body
        assert 'id="preview-skeleton-topn"' in body
        assert 'id="preview-skeleton-narrated"' in body
        assert 'id="preview-duration-fill"' in body

    async def test_phone_preview_has_frame_and_no_inside_purple_bg(self, controller):
        body = body_of(await controller.new_project_page())
        phone_part = body.split('id="new-project-preview-phone"')[1]
        phone_part = phone_part.split('form="create-project-form"')[0]
        assert 'id="preview-phone-frame"' in phone_part
        assert "rounded-[3.4rem]" in phone_part
        assert "w-[360px]" in phone_part
        assert "h-full min-h-[700px]" in phone_part
        assert "items-start" in phone_part
        assert "border-foreground/10" in phone_part
        assert "bg-primary/20" not in phone_part
        assert "from-primary" not in phone_part
        assert "to-primary" not in phone_part

    async def test_preview_label_is_neutral(self, controller):
        body = body_of(await controller.new_project_page())
        assert "EN VIVO" not in body
        assert "VIVO" not in body
        assert ">PREVIEW<" in body

    async def test_preview_json_contains_topn_skeleton_and_range(self, controller):
        body = body_of(await controller.new_project_page())
        assert "__PREVIEW_JSON__" in body
        blob = json.loads(body.split("__PREVIEW_JSON__ = ")[1].split(";")[0])
        topn = blob["formats"]["topn"]
        assert topn["duration_range"] == [35, 50]
        assert len(topn["skeleton"]) == 7  # hook + 5 items + conclusion
        assert topn["skeleton"][1]["num"] == "1"
        assert topn["skeleton"][5]["num"] == "5"
        assert "narrated" in blob["formats"]
        assert blob["formats"]["narrated"]["caption_styles"] == ["highlight", "plain"]

    async def test_preview_js_mirrors_format_hook_and_caption(self, controller):
        body = body_of(await controller.new_project_page())
        assert "new-project-title" in body and "preview-hook-block" in body
        assert "preview-title" not in body and 'id="preview-hook"' not in body
        assert "preview-caption-highlight" in body
        assert "preview-caption-plain" in body

    async def test_topic_selection_triggers_preview_mirror(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'src="/static/js/project-form.js"' in body
        selected = FORM_JS.split("function selectFramework(")[1]
        assert "mirrorPreview();" in selected

    async def test_thumbs_render_for_format_topic_and_style(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'id="format-btn-narrated"' in body
        assert 'id="format-btn-topn"' in body
        assert 'id="cap-btn-highlight"' in body
        assert 'id="cap-btn-plain"' in body
        form_part = body.split('id="create-project-form"')[1]
        assert form_part.count("overflow-x-auto") == 3

    async def test_format_thumbs_above_topic_thumbs(self, controller):
        body = body_of(await controller.new_project_page())
        assert body.index('id="format-btn-') < body.index('id="type-btn-')

    async def test_focus_sits_within_topic_section_below_thumbs(self, controller):
        body = body_of(await controller.new_project_page())
        assert body.index('id="new-project-title"') < body.index('id="format-btn-')
        assert body.index('id="type-btn-') < body.index('id="new-project-focus"')

    async def test_hidden_selects_keep_post_names(self, controller):
        body = body_of(await controller.new_project_page())
        assert body.count('name="format"') == 1
        assert body.count('name="caption_style"') == 1
        assert 'id="new-project-format"' in body
        assert 'id="new-project-caption-style"' in body


class TestPreviewBackground:
    """The phone screen shows random stock-style media (video or image) behind
    the mirrored content, like the real pipeline's background selection."""

    async def test_background_is_video_when_picked(self, controller, monkeypatch):
        from shorts_creator.ui.pages import new_project as np

        monkeypatch.setattr(np, "_pick_preview_background", lambda: ("video", "/api/preview/clip"))
        body = body_of(await controller.new_project_page())
        assert "<video" in body
        assert 'src="/api/preview/clip"' in body
        assert "object-cover" in body

    async def test_background_is_image_when_picked(self, controller, monkeypatch):
        from shorts_creator.ui.pages import new_project as np

        monkeypatch.setattr(
            np,
            "_pick_preview_background",
            lambda: ("image", "https://picsum.photos/seed/42/540/960"),
        )
        body = body_of(await controller.new_project_page())
        assert "<img" in body
        assert "https://picsum.photos/seed/42/540/960" in body
        assert "object-cover" in body

    async def test_content_raised_above_background_with_scrim(self, controller, monkeypatch):
        from shorts_creator.ui.pages import new_project as np

        monkeypatch.setattr(
            np,
            "_pick_preview_background",
            lambda: ("image", "https://picsum.photos/seed/1/540/960"),
        )
        body = body_of(await controller.new_project_page())
        assert "bg-foreground/20" in body
        assert "relative z-10" in body
        assert body.index("<img") < body.index("9:41")


class TestRealTextStyles:
    """Preview text mirrors the renderer's fonts, sizes, colors and placement
    (pipeline.py constants scaled from 1080x1920 down to the 360px screen)."""

    async def test_uses_real_renderer_font_via_font_face(self, controller):
        body = body_of(await controller.new_project_page())
        assert "@font-face" in body
        assert "PreviewDejaVu" in body
        assert "url('/api/preview/font')" in body

    async def test_caption_uses_scaled_renderer_size_stroke_and_pill(self, controller):
        body = body_of(await controller.new_project_page())
        assert "font-size: 18.67px" in body  # CAPTION_FONT_SIZE 56 / 3
        assert "-webkit-text-stroke: 0.67px #000" in body  # CAPTION_OUTLINE_WIDTH 2 / 3
        assert "#7C5CFA" in body  # CAPTION_HIGHLIGHT_COLOUR pill
        assert "pv-pill" in body
        assert "pv-cap" in body

    async def test_hook_lines_use_black_pills_with_renderer_fit(self, controller):
        body = body_of(await controller.new_project_page())
        assert "rgba(0,0,0,0.75)" in body  # hook pill 0x000000C0
        assert "pv-hook block" in body
        for word in ["The", "hook", "that", "stops", "the", "scroll"]:
            assert f">>{word}<<" in body or f">{word}<" in body
        assert (
            body.count('class="pv-hook block"') == 6
        )  # one pill per hook word (HOOK_LINE_TARGET_SIZE = 1)
        assert "font-size:36.67px" in body  # compose.fit → 110px scaled by 360/1080

    async def test_caption_centered_like_renderer(self, controller):
        body = body_of(await controller.new_project_page())
        assert body.index('id="preview-caption"') > body.index('id="preview-skeleton-topn"')
        assert "flex-1 flex flex-col justify-center" in body

    async def test_preview_js_rebuilds_hook_pills_from_skeleton(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'src="/static/js/composer-preview.js"' in body
        js = PREVIEW_JS.split("function mirrorPreview()")[1]
        assert "info.skeleton || []" in js
        assert "return r.label === 'Hook';" in js
        assert (
            "_pvFitHookFont(hookWords, wf, (info.palette || {}).highlight_colour || _pvTokenHex('--primary', '0x7C5CFAFF'))"
            in js
        )
        assert "s.className = 'pv-hook block';" in js
        assert "hookBlock.appendChild(s)" in js

    async def test_preview_js_hook_font_fit_mirrors_compose(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'src="/static/js/composer-preview.js"' in body
        js = PREVIEW_JS.split("function _pvFitHookFont")[1]
        assert "(wf * 1080) / (maxChars * 0.55)" in js
        assert "var wf = widthFactor || 0.80;" in js
        assert "(0.70 * 1920) / (texts.length * 1.3)" in js
        assert "Math.max(40, Math.min(110" in js
        assert "Math.round(size * 360 / 1080 * 100) / 100" in js


class TestTopicMeta:
    """Every registered topic gets real styling, not the generic folder fallback
    (and no dead topics are left behind)."""

    async def test_all_topics_have_styled_meta(self, controller):
        from shorts_creator.ui.pages import new_project as np

        for name in ("self_improvement", "psychology", "stoic"):
            meta = np._TYPE_INFO[name]
            assert meta["emoji"] and meta["desc"]
            assert "from-" in meta["color_active"]

    async def test_no_dead_storytelling_topic(self, controller):
        from shorts_creator.ui.pages import new_project as np

        assert "storytelling" not in np._TYPE_INFO

    async def test_topic_buttons_show_emoji_and_desc(self, controller):
        body = body_of(await controller.new_project_page())
        assert "🔬" in body and "Research-grounded psychology" in body
        assert "🏛️" in body and "Timeless Stoic philosophy" in body


class TestDurationRangeHint:
    """The duration field hints at the selected format's real render range and
    flags values outside it."""

    async def test_hint_renders_for_default_format(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'id="duration-range-hint"' in body
        assert "Narrated renders 38\u201350s" in body

    async def test_js_updates_hint_from_selected_format(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'src="/static/js/composer-preview.js"' in body
        js = PREVIEW_JS.split("function mirrorPreview()")[1]
        assert "duration-range-hint" in js
        assert "renders ' + rng[0] + " in js
        assert "raw < rng[0] || raw > rng[1]" in js
        assert "rgb(var(--color-warning-channels))" in js


class TestTopicAwareSkeleton:
    """The Story pane labels narrated rows from the topic's own
    structure_sections, matching how the reel is actually scripted."""

    async def test_default_topic_labels_narrated_rows(self, controller):
        body = body_of(await controller.new_project_page())
        assert ">message<" in body and ">metaphor<" in body

    async def test_topn_skeleton_keeps_numbered_items(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'id="preview-skeleton-topn"' in body
        assert ">1<" in body and ">5<" in body

    async def test_js_relabels_mid_rows_per_topic(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'src="/static/js/composer-preview.js"' in body
        js = PREVIEW_JS.split("function mirrorPreview()")[1]
        assert ".skel-mid-label" in js
        assert "midLabels[i].textContent = i < midSections.length" in js
        assert "s !== 'hook' && s !== 'conclusion' && s !== 'top_items'" in js


class TestPreviewBackgroundPicker:
    """The preview mirror uses bundled nature footage whenever it exists and
    only falls back to a random remote image when the app has no clips."""

    async def test_picker_returns_local_clip_when_footage_exists(
        self, controller, monkeypatch, tmp_path
    ):
        from shorts_creator.ui.pages import new_project as np

        clip_dir = tmp_path / "clip"
        clip_dir.mkdir()
        (clip_dir / "sample_nature_asmr.mp4").touch()
        monkeypatch.setattr(np, "ASSETS_ROOT", tmp_path)
        assert np._pick_preview_background() == ("video", "/api/preview/clip")

    async def test_picker_falls_back_to_remote_image_without_clips(
        self, controller, monkeypatch, tmp_path
    ):
        from shorts_creator.ui.pages import new_project as np

        monkeypatch.setattr(np, "ASSETS_ROOT", tmp_path)
        assert np._pick_preview_background()[0] == "image"


class TestPreviewSectionTabs:
    async def test_tabs_inline_with_preview_label(self, controller):
        body = body_of(await controller.new_project_page())
        assert body.index(">PREVIEW<") < body.index('id="preview-section-tabs"')
        assert body.index('id="preview-section-tabs"') < body.index('id="preview-phone-frame"')
        names = ["intro", "mid", "outro", "full"]
        for i, name in enumerate(names):
            assert f'data-preview-section="{name}"' in body
            assert f"setPreviewSection(&#x27;{name}&#x27;)" in body
            if i:
                assert body.index(f'data-preview-section="{names[i - 1]}"') < body.index(
                    f'data-preview-section="{name}"'
                )

    async def test_full_tab_active_by_default(self, controller):
        body = body_of(await controller.new_project_page())
        full_tag = body.split('data-preview-section="full"')[1].split(">")[0]
        assert "bg-primary" in full_tag
        assert 'aria-pressed="true"' in full_tag
        intro_tag = body.split('data-preview-section="intro"')[1].split(">")[0]
        assert "bg-primary" not in intro_tag
        assert 'aria-pressed="false"' in intro_tag

    async def test_phone_has_section_layer_ids(self, controller):
        body = body_of(await controller.new_project_page())
        for el_id in (
            "preview-bg-layer",
            "preview-hook-block",
            "preview-mid-block",
            "preview-duration-bar",
            "preview-caption",
            "preview-duration-fill",
        ):
            assert f'id="{el_id}"' in body

    async def test_outro_layer_matches_default_clip(self, controller):
        body = body_of(await controller.new_project_page())
        outro_tag = body.split('id="preview-outro"')[1].split(">")[0]
        assert "display:none" in outro_tag
        assert "background:#0a0a32" in outro_tag
        outro = body.split('id="preview-outro"')[1].split("</div>")[0]
        assert "Thanks for watching" in outro
        assert "text-[32px]" in outro

    async def test_hook_and_caption_in_centered_content_region(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'id="preview-hook-block" class="text-center"' in body
        assert "text-center mt-3" not in body
        region = body.split('class="flex-1 flex flex-col justify-center gap-8 px-1"')[1]
        region = region.split('id="preview-duration-bar"')[0]
        assert 'id="preview-hook-block"' in region
        assert 'id="preview-mid-block"' in region
        assert body.index('id="preview-hook-block"') < body.index('id="preview-mid-block"')

    async def test_section_js_toggles_layers(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'src="/static/js/composer-preview.js"' in body
        assert "function setPreviewSection" in PREVIEW_JS
        js = PREVIEW_JS.split("function setPreviewSection")[1]
        assert js.count("_pvSetDisplay(") == 6
        assert "_pvSetDisplay('preview-outro', s.outro);" in js
        for name in ("intro", "mid", "outro", "full"):
            assert f"{name}:" in js
        assert "intro: { bg: true, hook: true, mid: false, dur: false, outro: false }" in js
        assert "outro: { bg: false, hook: false, mid: false, dur: false, outro: true }" in js


class TestPreviewPlayback:
    async def test_play_button_present(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'id="preview-play-btn"' in body
        assert 'onclick="togglePreviewPlay()"' in body
        assert 'id="preview-play-icon"' in body
        assert 'id="preview-pause-icon"' in body
        assert 'style="display:none"' in body.split('id="preview-pause-icon"')[1].split(">")[0]
        assert 'aria-label="Play or pause preview"' in body

    async def test_caption_seeded_with_skeleton_content(self, controller):
        body = body_of(await controller.new_project_page())
        assert "First practice, kept concrete" in body
        assert "the whole caption" not in body

    async def test_timeline_ticks_in_duration_bar(self, controller):
        body = body_of(await controller.new_project_page())
        bar = body.split('id="preview-duration-bar"')[1].split('id="preview-play-btn"')[0]
        assert 'id="preview-timeline-ticks"' in bar
        assert bar.count("w-px bg-foreground/50") == 2

    async def test_tab_click_autoplays_section(self, controller):
        js = PREVIEW_JS.split("function setPreviewSection")[1]
        assert "_pvMode = name;" in js
        assert "_pvProgress = 0;" in js
        assert "if (!_pvPlaying) togglePreviewPlay();" in js
        assert "_pvRenderFrame();" in js

    async def test_playback_engine_present(self, controller):
        js = PREVIEW_JS.split("function togglePreviewPlay")[1]
        for fn in (
            "_pvTick",
            "_pvRenderFrame",
            "_pvRenderCaption",
            "_pvShowOnly",
            "_pvPositionTicks",
        ):
            assert fn in js
        assert "var _pvIntroFrac = 0.15;" in PREVIEW_JS
        assert "var _pvOutroFrac = 0.10;" in PREVIEW_JS
        assert "setInterval(_pvTick, 100)" in js
        assert "_preview_data.formats[fmtName] || {}).skeleton || []" in PREVIEW_JS
        assert "fill.style.width = Math.round(_pvBarProgress() * 100) + '%'" in PREVIEW_JS
        assert "_pvProgress += 0.1 / (_pvTotalSeconds() * _pvWindowLen())" in PREVIEW_JS
        assert "1 - _pvOutroFrac) + _pvOutroFrac * _pvProgress" in PREVIEW_JS

    async def test_paused_bar_visible_only_on_full_tab(self, controller):
        js = PREVIEW_JS.split("function _pvShowOnly")[1]
        assert "_pvPlaying || _pvProgress > 0 || _pvMode === 'full'" in js


class TestTopnStylelessPreview:
    """Top N is style-less (no captions) but shows its ranked item screens:
    the hook in intro and numbered item pills in mid - compose.py builds
    rank_<idx> overlays for top_items lines. The phone preview must mirror
    that, not Narrated's caption flow."""

    async def test_styleless_flag_drives_hook_and_caption_visibility(self, controller):
        assert "var _pvStyleLess = false;" in PREVIEW_JS
        assert "_pvStyleLess = info.caption_styles.length === 0 && !info.rank;" in PREVIEW_JS
        js = PREVIEW_JS.split("function togglePreviewPlay")[1]
        assert "!_pvStyleLess && which === 'hook'" in js
        assert "!_pvStyleLess && which === 'mid'" in js
        assert "s.hook && !_pvStyleLess" in js
        assert "s.mid && !_pvStyleLess" in js

    async def test_rank_flag_per_format_in_preview_data(self, controller):
        body = body_of(await controller.new_project_page())
        blob = _preview_data_blob(body)
        assert blob["formats"]["topn"]["rank"] is True
        assert blob["formats"]["narrated"]["rank"] is False

    async def test_ranking_block_markup_and_js(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'id="preview-ranking-block"' in body
        js = PREVIEW_JS.split("function _pvRankItems")[1]
        assert "_pvFitHookFont([item.num].concat(item.words))" in js
        assert "Math.round(pillFont * scale * 100) / 100" in js
        assert "var ns = document.getElementById('new-project-numbered-scale');" in js
        assert "n.className = 'pv-hook block';" in js
        assert "r.num && r.text" in js

    async def test_playback_cycles_ranked_items_in_mid(self, controller):
        js = PREVIEW_JS.split("function _pvRenderFrame")[1]
        assert "_pvRankMode()" in js
        assert "_pvRenderRanking(Math.min(items.length - 1, Math.floor(frac * items.length)))" in js
        assert "_pvSetDisplay('preview-ranking-block', _pvRankMode() && which === 'mid')" in js
        assert "_pvSetDisplay('preview-ranking-block', s.mid && _pvRankMode())" in js


class TestComposerFormOverrides:
    async def test_create_maps_composer_fields(self, controller):

        from shorts_creator.ui.pages.new_project import form_overrides

        resolved = await controller._resolve_creation_profile("self_improvement")
        overrides = form_overrides(
            {
                "format": "narrated",
                "duration_seconds": "45",
                "pacing_wps": "2.7",
                "hook_text": "My custom hook",
                "sections": '["message"]',
                "section_texts": '{"message": "My line"}',
                "style": '{"chunk_size": 2}',
                "palette": '{"highlight_colour": "0xFF0000AA"}',
                "layout": '{"anchor": "lower_third"}',
                "stages": '{"music": true}',
            },
            resolved,
        )
        assert overrides["pacing_wps"] == 2.7
        assert overrides["hook_text"] == "My custom hook"
        assert overrides["sections"] == ["message"]
        assert overrides["stages"] == {"music": True}
        assert overrides["layout"] == {"anchor": "lower_third"}
        assert overrides["style"] == {"chunk_size": 2}
        assert overrides["palette"] == {"highlight_colour": "0xFF0000AA"}


class TestComposerPanels:
    async def test_content_panel_controls_present(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'id="new-project-pacing"' in body
        assert 'id="new-project-hook-text"' in body
        assert 'id="new-project-sections"' in body
        assert 'id="composer-content-panel"' in body

    async def test_style_panel_controls_present(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'id="new-project-chunk-size"' in body
        assert 'id="new-project-highlight-colour"' in body
        assert 'id="composer-style-panel"' in body

    async def test_placement_panel_controls_present(self, controller):
        body = body_of(await controller.new_project_page())
        assert 'id="new-project-anchor"' in body
        assert 'id="new-project-block-width"' in body
        assert 'id="new-project-numbered-scale"' in body
        assert 'id="new-project-pill-mode"' in body
        assert 'id="composer-placement-panel"' in body

    async def test_preview_data_carries_layout_and_palette(self, controller):
        body = body_of(await controller.new_project_page())
        blob = _preview_data_blob(body)
        fmt = blob["formats"]["narrated"]
        assert fmt["layout"]["anchor"] == "center"
        assert fmt["layout"]["block_width_pct"] == [60, 95]
        assert fmt["palette"]["highlight_colour"] == "0x7C5CFAFF"
        assert fmt["pacing_wps_range"] == [2.5, 3.0]

    async def test_spec_tab_js_serializes_resolved_spec(self, controller):
        js = PREVIEW_JS.split("function serializeResolvedSpec")[1]
        assert "spec-json" in js
        assert "new-project-pacing" in js
        assert "hook_text" in js


class TestMediaPanelBgMode:
    """Create page renders the Background Video/Image control with video as
    the default checked state."""

    async def test_media_panel_renders_bg_mode_radios(self, controller):
        body = body_of(await controller.new_project_page())
        panel = body.split('id="composer-media-panel"')[1]
        assert 'name="bg_mode"' in panel
        assert 'value="video" checked' in panel
        assert 'value="image"' in panel
        assert 'id="bg-clip-picker-wrapper"' in panel
        assert "Background clip" in panel


class TestPlaybackControls:
    """Pausing the simulated preview must also pause the background video and
    surface where in time the preview froze; play resumes from that spot."""

    async def test_background_video_has_controls_wiring_id(self, controller):
        body = body_of(await controller.new_project_page())
        assert "<video" in body
        assert 'id="preview-bg-video"' in body

    async def test_position_readout_always_visible(self, controller):
        body = body_of(await controller.new_project_page())
        marker = 'id="preview-position-display"'
        assert marker in body
        assert "display:none" not in body.split(marker)[0][-200:]
        assert "0:00 / 0:30" in body

    async def test_playback_controls_sync_video_and_position(self, controller):
        js = PREVIEW_JS.split("function togglePreviewPlay")[1]
        assert "_pvSyncVideo();" in js
        assert "_pvUpdatePositionDisplay();" in js
        js2 = PREVIEW_JS.split("function _pvTick")[1]
        assert "preview-bg-video" in js2

    async def test_duration_bar_kept_while_paused_with_position(self, controller):
        js = PREVIEW_JS.split("function _pvShowOnly")[1]
        assert "_pvPlaying || _pvProgress > 0 || _pvMode === 'full'" in js
