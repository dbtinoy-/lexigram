"""Guided project creation page (facade module).

The implementation lives in sibling ``new_project_*`` modules (profile,
overrides, wizard, preview, panels, main, settings). This module keeps the
stable ``shorts_creator.ui.pages.new_project`` import path and re-exports the
page helpers consumed by controllers and tests.
"""

from shorts_creator.ui.pages.new_project_main import (
    _compose_steps_strip,
    _composer_preview_json,
    composer_preview_js,
    new_project_form,
)
from shorts_creator.ui.pages.new_project_overrides import form_overrides
from shorts_creator.ui.pages.new_project_panels import _TYPE_INFO, _media_panel, _phase2_panel
from shorts_creator.ui.pages.new_project_preview import (
    _pick_preview_background,
    _preview_phone,
    preview_styles,
)
from shorts_creator.ui.pages.new_project_profile import _profile_strip, fallback_profile
from shorts_creator.ui.pages.new_project_settings import project_settings_form
from shorts_creator.ui.pages.new_project_wizard import _wizard_caption_field

__all__ = [
    "_TYPE_INFO",
    "_compose_steps_strip",
    "_composer_preview_json",
    "_media_panel",
    "_phase2_panel",
    "_pick_preview_background",
    "_preview_phone",
    "_profile_strip",
    "_wizard_caption_field",
    "composer_preview_js",
    "fallback_profile",
    "form_overrides",
    "new_project_form",
    "preview_styles",
    "project_settings_form",
]
