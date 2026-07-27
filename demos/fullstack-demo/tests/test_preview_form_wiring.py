"""Contract test: the live phone preview must be fed by the actual form
fields in BOTH the create-project form and the edit/settings form.

The preview JS (composer-preview.js) reads form widgets by id and writes
preview nodes by id; several of those reads are unguarded, so every id on
both lists must exist in both server-rendered forms or the preview crashes.
This mirrors the wiring documented in
tests/../src/shorts_creator/ui/static/js/composer-preview.js.
"""

from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.ui.pages.new_project import new_project_form, project_settings_form


def _project(project_id="p1"):
    class _Project:
        id = project_id
        title = "My Short"

    return _Project()


def _resolved(value, source):
    return ResolvedSetting(
        value=value, source=source, is_overridden=source is ProfileSource.PROJECT
    )


def _settings_profile() -> EffectiveProjectProfile:
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
    }
    return EffectiveProjectProfile(**data)


def _render_both():
    create_html = str(new_project_form())
    settings_html = str(
        project_settings_form(
            _project(),
            _settings_profile(),
            {
                "music": [("m1", "Lo-fi")],
                "font": [("f1", "Inter")],
                "bg_clip": [("bg1", "City")],
                "outro_clip": [("o1", "Outro")],
                "watermark": [("w1", "Mark")],
            },
        )
    )
    return create_html, settings_html


# Nodes the preview writes to. preview-duration-fill, preview-caption-highlight
# and preview-caption-plain are dereferenced without a null guard in
# mirrorPreview(), so their absence would crash the page JS.
PREVIEW_NODES = [
    "new-project-preview-phone",
    "preview-hook-block",
    "preview-caption",
    "preview-caption-highlight",
    "preview-caption-plain",
    "preview-duration-fill",
    "preview-duration-bar",
    "preview-timeline-ticks",
    "preview-topic-dot",
    "preview-ranking-block",
    "preview-bg-layer",
    "preview-outro",
    "preview-mid-block",
    "preview-play-btn",
    "duration-range-hint",
]

# Form widgets the preview reads (`mirrorPreview` + the widget binding list at
# the bottom of composer-preview.js + the summary/structured readers).
PREVIEW_WIDGETS = [
    "new-project-title",
    "new-project-format",
    "new-project-duration",
    "new-project-caption-style",
    "new-project-type",
    "new-project-pacing",
    "new-project-hook-text",
    "new-project-outro-text",
    "new-project-sections",
    "new-project-chunk-size",
    "new-project-highlight-colour",
    "new-project-pill-colour",
    "new-project-caption-size",
    "new-project-outline-width",
    "new-project-block-width",
    "new-project-numbered-scale",
    "new-project-pill-mode",
    "new-project-uppercase",
    "new-project-scrim",
    "new-project-watermark-corner",
    "new-project-watermark-size",
    "new-project-watermark-opacity",
    "new-project-music-volume",
    "new-project-music-fade",
    "new-project-fade-out",
    "new-project-motion",
    "new-project-emphasis",
    "new-project-loudness",
    "new-project-audio-normalize",
    "new-project-hold-hook",
    "new-project-message-pacing",
    "new-project-hold-conclusion",
    "new-project-stage-accent-hook",
    "new-project-stage-accent-message",
    "new-project-stage-accent-metaphor",
    "new-project-stage-accent-conclusion",
    "new-project-layout-json",
    "new-project-stages-json",
    "new-project-background-motion-json",
    "new-project-loudness-json",
    "new-project-audio-normalize-json",
    "new-project-section-holds-json",
    "new-project-stage-accents-json",
    "new-project-asset-bg_clip-source",
    "new-project-asset-bg_clip",
    "new-project-asset-bg_clip-url",
    "new-project-asset-bg_clip-provider",
    "new-project-asset-music-source",
    "new-project-asset-music",
    "new-project-asset-music-url",
    "new-project-asset-outro_clip-source",
    "new-project-asset-outro_clip",
    "new-project-asset-outro_clip-url",
    "new-project-asset-watermark-source",
    "new-project-asset-watermark",
    "new-project-asset-watermark-url",
    "new-project-asset-font",
]

OUTCOME_NODES = ["composer-summary", "spec-json", "spec-structured"]

# style-json / palette-json are NOT server-rendered: syncComposerHidden()
# creates both hidden inputs on init (with name attributes for submission)
# before any user interaction. The node-level harness in
# composer-preview.js's test run proves that creation path; the forms only
# need to render their parent panel.
STYLE_PANELS = ["composer-style-panel"]


class TestCreateFormPreviewWiring:
    def test_create_form_emits_all_preview_nodes(self):
        html, _ = _render_both()
        missing = [n for n in PREVIEW_NODES if f'id="{n}"' not in html]
        assert not missing, f"create form missing preview nodes: {missing}"

    def test_create_form_emits_all_preview_widgets(self):
        html, _ = _render_both()
        missing = [w for w in PREVIEW_WIDGETS if f'id="{w}"' not in html]
        missing += ["new-project-focus"] if 'id="new-project-focus"' not in html else []
        assert not missing, f"create form missing preview widgets: {missing}"

    def test_create_form_emits_outcome_nodes(self):
        html, _ = _render_both()
        missing = [n for n in OUTCOME_NODES if f'id="{n}"' not in html]
        assert not missing, f"create form missing outcome nodes: {missing}"

    def test_create_form_loads_composer_preview_js(self):
        html, _ = _render_both()
        assert "static/js/composer-preview.js" in html


class TestSettingsFormPreviewWiring:
    def test_settings_form_emits_all_preview_nodes(self):
        _, html = _render_both()
        missing = [n for n in PREVIEW_NODES if f'id="{n}"' not in html]
        assert not missing, f"settings form missing preview nodes: {missing}"

    def test_settings_form_emits_all_preview_widgets(self):
        _, html = _render_both()
        missing = [w for w in PREVIEW_WIDGETS if f'id="{w}"' not in html]
        assert not missing, f"settings form missing preview widgets: {missing}"

    def test_settings_form_emits_outcome_nodes(self):
        _, html = _render_both()
        missing = [n for n in OUTCOME_NODES if f'id="{n}"' not in html]
        assert not missing, f"settings form missing outcome nodes: {missing}"

    def test_settings_form_loads_composer_preview_js(self):
        _, html = _render_both()
        assert "static/js/composer-preview.js" in html
