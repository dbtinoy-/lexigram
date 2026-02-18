"""P3 hook surface import verification for lexigram-ai-prompt."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest


def test_prompt_hooks_root_module_exists() -> None:
    import lexigram.ai.prompt
    from lexigram.ai.prompt.hooks import (
        PromptInputSanitizedHook,
        PromptRenderedHook,
        PromptTemplateResolvedHook,
    )

    assert (
        lexigram.ai.prompt.PromptTemplateResolvedHook is PromptTemplateResolvedHook
    )
    assert lexigram.ai.prompt.PromptRenderedHook is PromptRenderedHook
    assert lexigram.ai.prompt.PromptInputSanitizedHook is PromptInputSanitizedHook


def test_prompt_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.ai.prompt.hooks import (
        PromptInputSanitizedHook,
        PromptRenderedHook,
        PromptTemplateResolvedHook,
    )
    from lexigram.ai.prompt.rendering.engine import RenderFormat

    resolved = PromptTemplateResolvedHook(template_name="welcome")
    rendered = PromptRenderedHook(render_format=RenderFormat.JINJA2)
    sanitized = PromptInputSanitizedHook()

    assert is_dataclass(resolved)
    assert is_dataclass(rendered)
    assert is_dataclass(sanitized)
    assert [field.name for field in fields(resolved)] == ["template_name"]
    assert [field.name for field in fields(rendered)] == ["render_format"]
    assert [field.name for field in fields(sanitized)] == []

    with pytest.raises(TypeError):
        PromptTemplateResolvedHook("welcome")  # type: ignore[misc]

    with pytest.raises(TypeError):
        PromptRenderedHook("jinja2")  # type: ignore[misc]

    with pytest.raises(TypeError):
        PromptInputSanitizedHook("value")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        resolved.template_name = "goodbye"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        rendered.render_format = RenderFormat.SIMPLE  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        sanitized.new_field = "value"  # type: ignore[misc]
