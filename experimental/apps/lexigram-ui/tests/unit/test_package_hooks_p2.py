"""P2 hook surface import verification for lexigram-ui."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass

import pytest


def test_ui_hooks_root_module_exists() -> None:
    import lexigram.ui
    from lexigram.ui.hooks import (
        UIComponentRenderedHook,
        UITemplateRenderedHook,
    )

    assert UIComponentRenderedHook.__name__ == "UIComponentRenderedHook"
    assert UITemplateRenderedHook.__name__ == "UITemplateRenderedHook"
    assert lexigram.ui.UIComponentRenderedHook is UIComponentRenderedHook
    assert lexigram.ui.UITemplateRenderedHook is UITemplateRenderedHook


def test_ui_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.ui.hooks import UIComponentRenderedHook, UITemplateRenderedHook

    component = UIComponentRenderedHook(component_name="UserCard")
    template = UITemplateRenderedHook(template_name="partials/user_card.html")

    assert is_dataclass(component)
    assert is_dataclass(template)

    with pytest.raises(TypeError):
        UIComponentRenderedHook("UserCard")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        component.component_name = "other"  # type: ignore[misc]
