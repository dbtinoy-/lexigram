"""Option-driven adaptation tests (Task 12 Step 4).

Ports relaykit adapter behaviors under ``RelayOptions`` control.  Zero-value
options must never alter outgoing payloads.
"""

from __future__ import annotations

import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.claude import ClaudeMapper
from lexigram.ai.relay.mappers.gemini import GeminiMapper
from lexigram.contracts.ai.llm import ChatMessage
from lexigram.contracts.ai.relay.context import (
    ClaudeOptions,
    GeminiOptions,
    RelayOptions,
)
from lexigram.contracts.ai.relay.ir import RelayRequest

claude_mapper = ClaudeMapper()
gemini_mapper = GeminiMapper()


def claude_ir(**kwargs: object) -> RelayRequest:
    """Build a canonical request for the Claude mapper."""
    defaults: dict[str, object] = {
        "model": "claude-sonnet-4-5",
        "messages": [ChatMessage(role="user", content="hi")],
    }
    defaults.update(kwargs)
    return RelayRequest(**defaults)  # type: ignore[arg-type]


def gemini_ir(**kwargs: object) -> RelayRequest:
    """Build a canonical request for the Gemini mapper."""
    defaults: dict[str, object] = {
        "model": "gemini-2.5-flash",
        "messages": [ChatMessage(role="user", content="hi")],
    }
    defaults.update(kwargs)
    return RelayRequest(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def ctx() -> ConversionContext:
    """A zero-value conversion context."""
    return ConversionContext()


# -- Claude: default max_tokens ----------------------------------------------


def test_claude_default_max_tokens_injected(ctx: ConversionContext) -> None:
    """A configured default fills a missing max_tokens."""
    ctx = ConversionContext(default_max_tokens=lambda _model: 8192)
    request = claude_mapper.ir_to_request(
        claude_ir(model="claude-sonnet-4-5"), context=ctx
    ).unwrap()
    assert request.max_tokens == 8192


def test_claude_client_max_tokens_wins(ctx: ConversionContext) -> None:
    """An explicit max_tokens beats the default callback."""
    ctx = ConversionContext(default_max_tokens=lambda _model: 8192)
    request = claude_mapper.ir_to_request(
        claude_ir(model="claude-sonnet-4-5", max_tokens=256), context=ctx
    ).unwrap()
    assert request.max_tokens == 256


# -- Claude: -thinking adapter -----------------------------------------------


def test_claude_thinking_adapter_adapts_suffix_model() -> None:
    """The -thinking adapter floors, budgets, pins sampling, and trims."""
    options = RelayOptions(
        claude=ClaudeOptions(
            thinking_adapter_enabled=True,
            thinking_budget_percentage=50,
            minimum_max_tokens=1280,
        )
    )
    ctx = ConversionContext(options=options)
    request = claude_mapper.ir_to_request(
        claude_ir(
            model="claude-3-7-sonnet-thinking",
            max_tokens=1000,
            temperature=0.9,
            top_p=0.5,
        ),
        context=ctx,
    ).unwrap()
    assert request.model == "claude-3-7-sonnet"
    assert request.max_tokens == 1280
    assert request.thinking == {"type": "enabled", "budget_tokens": 640}
    assert request.temperature == 1.0
    assert request.top_p is None


def test_claude_thinking_adapter_budget_from_max_tokens() -> None:
    """budget_tokens is a percentage of the adapted max_tokens."""
    options = RelayOptions(
        claude=ClaudeOptions(
            thinking_adapter_enabled=True,
            thinking_budget_percentage=25,
            minimum_max_tokens=1280,
        )
    )
    ctx = ConversionContext(options=options)
    request = claude_mapper.ir_to_request(
        claude_ir(model="claude-3-7-sonnet-thinking", max_tokens=2048),
        context=ctx,
    ).unwrap()
    assert request.max_tokens == 2048
    assert request.thinking == {"type": "enabled", "budget_tokens": 512}


def test_claude_thinking_adapter_preserves_suffix_when_flagged() -> None:
    """model_suffix_preserved keeps the -thinking name on the wire."""
    options = RelayOptions(
        claude=ClaudeOptions(
            thinking_adapter_enabled=True, thinking_budget_percentage=50
        ),
        model_suffix_preserved=True,
    )
    ctx = ConversionContext(options=options)
    request = claude_mapper.ir_to_request(
        claude_ir(model="claude-3-7-sonnet-thinking", max_tokens=1024),
        context=ctx,
    ).unwrap()
    assert request.model == "claude-3-7-sonnet-thinking"
    assert request.thinking == {"type": "enabled", "budget_tokens": 512}


def test_claude_thinking_adapter_preserves_suffix_via_callback() -> None:
    """The preserve-thinking-suffix callback also keeps the suffix."""
    options = RelayOptions(
        claude=ClaudeOptions(
            thinking_adapter_enabled=True, thinking_budget_percentage=50
        ),
    )
    ctx = ConversionContext(
        options=options,
        preserve_thinking_suffix=lambda model: model == "claude-3-7-sonnet-thinking",
    )
    request = claude_mapper.ir_to_request(
        claude_ir(model="claude-3-7-sonnet-thinking", max_tokens=1024),
        context=ctx,
    ).unwrap()
    assert request.model == "claude-3-7-sonnet-thinking"


def test_claude_thinking_adapter_inactive_without_suffix() -> None:
    """No -thinking suffix means the adapter leaves the payload alone."""
    options = RelayOptions(
        claude=ClaudeOptions(
            thinking_adapter_enabled=True,
            thinking_budget_percentage=50,
            minimum_max_tokens=1280,
        )
    )
    ctx = ConversionContext(options=options)
    request = claude_mapper.ir_to_request(
        claude_ir(
            model="claude-3-7-sonnet", max_tokens=500, temperature=0.9, top_p=0.5
        ),
        context=ctx,
    ).unwrap()
    assert request.model == "claude-3-7-sonnet"
    assert request.max_tokens == 500
    assert request.thinking is None
    assert request.temperature == 0.9
    assert request.top_p == 0.5


def test_claude_thinking_adapter_records_floor_loss() -> None:
    """Flooring max_tokens records a semantic-loss warning."""
    options = RelayOptions(
        claude=ClaudeOptions(
            thinking_adapter_enabled=True,
            thinking_budget_percentage=50,
            minimum_max_tokens=1280,
        )
    )
    ctx = ConversionContext(options=options)
    claude_mapper.ir_to_request(
        claude_ir(model="claude-3-7-sonnet-thinking", max_tokens=1000),
        context=ctx,
    ).unwrap()
    assert any(loss.reason == "max_tokens_floored" for loss in ctx.losses)


# -- Claude: zero-value options are inert ------------------------------------


def test_claude_zero_value_options_leave_payload_unchanged(
    ctx: ConversionContext,
) -> None:
    """Zero-value options never mutate model, sampling, or thinking."""
    request = claude_mapper.ir_to_request(
        claude_ir(
            model="claude-3-7-sonnet-thinking",
            max_tokens=1024,
            temperature=0.7,
            top_p=0.9,
        ),
        context=ctx,
    ).unwrap()
    assert request.model == "claude-3-7-sonnet-thinking"
    assert request.max_tokens == 1024
    assert request.temperature == 0.7
    assert request.top_p == 0.9
    assert request.thinking is None
    assert ctx.losses == []


# -- Gemini: thinking adapter ------------------------------------------------


def test_gemini_zero_value_options_no_thinking_config(ctx: ConversionContext) -> None:
    """A zero-value context adds no thinkingConfig to the payload."""
    request = gemini_mapper.ir_to_request(
        gemini_ir(model="gemini-2.5-flash", max_tokens=100), context=ctx
    ).unwrap()
    assert "thinkingConfig" not in request.generation_config


def test_gemini_thinking_adapter_injects_budget() -> None:
    """The adapter adds thinkingBudget when enabled with a budget."""
    options = RelayOptions(
        gemini=GeminiOptions(thinking_adapter_enabled=True, thinking_budget=4096)
    )
    ctx = ConversionContext(options=options)
    request = gemini_mapper.ir_to_request(
        gemini_ir(model="gemini-2.5-flash", max_tokens=100), context=ctx
    ).unwrap()
    assert request.generation_config["thinkingConfig"] == {"thinkingBudget": 4096}


def test_gemini_thinking_adapter_inert_without_budget() -> None:
    """Enabled adapter with a zero budget adds nothing."""
    options = RelayOptions(gemini=GeminiOptions(thinking_adapter_enabled=True))
    ctx = ConversionContext(options=options)
    request = gemini_mapper.ir_to_request(
        gemini_ir(model="gemini-2.5-flash", max_tokens=100), context=ctx
    ).unwrap()
    assert "thinkingConfig" not in request.generation_config


# -- Gemini: safety settings -------------------------------------------------


def test_gemini_safety_settings_callback() -> None:
    """Safety thresholds come from the host callback, not metadata."""
    ctx = ConversionContext(
        safety_setting=lambda category: (
            "BLOCK_NONE" if category == "HARM_CATEGORY_HARASSMENT" else None
        )
    )
    request = gemini_mapper.ir_to_request(
        gemini_ir(model="gemini-2.5-flash"), context=ctx
    ).unwrap()
    assert request.safety_settings == [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}
    ]


def test_gemini_safety_settings_absent_by_default(ctx: ConversionContext) -> None:
    """Nil callback yields no safetySettings."""
    request = gemini_mapper.ir_to_request(gemini_ir(), context=ctx).unwrap()
    assert request.safety_settings is None


# -- Gemini: image-generation modalities -------------------------------------


def test_gemini_image_modalities_when_supported() -> None:
    """Imagine-capable models advertise TEXT + IMAGE modalities."""
    ctx = ConversionContext(
        supports_image_generation=lambda model: model == "gemini-2.5-flash-image"
    )
    request = gemini_mapper.ir_to_request(
        gemini_ir(model="gemini-2.5-flash-image", max_tokens=100), context=ctx
    ).unwrap()
    assert request.generation_config["responseModalities"] == ["TEXT", "IMAGE"]


def test_gemini_image_modalities_absent_by_default(ctx: ConversionContext) -> None:
    """Imagination-capability callback off adds no modalities."""
    request = gemini_mapper.ir_to_request(
        gemini_ir(model="gemini-2.5-flash-image", max_tokens=100), context=ctx
    ).unwrap()
    assert "responseModalities" not in request.generation_config
