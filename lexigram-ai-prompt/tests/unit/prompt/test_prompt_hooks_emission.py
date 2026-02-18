"""Tests for PromptService hook emission and the render-format-aware observer.

Hooks are emitted fire-and-forget through the framework :class:`HookRegistry`,
so these tests render inside a running event loop and settle the scheduled
tasks with a ``sleep(0)``.
"""

from __future__ import annotations

import asyncio

import pytest

from lexigram.ai.prompt.hooks import (
    PromptInputSanitizedHook,
    PromptRenderedHook,
    PromptTemplateResolvedHook,
)
from lexigram.ai.prompt.rendering.engine import RenderFormat
from lexigram.ai.prompt.rendering.sanitizer import InputSanitizer
from lexigram.ai.prompt.service.models import PromptRenderRequest, PromptTemplate
from lexigram.ai.prompt.service.observer import NoOpPromptObserver, PromptObserverProtocol
from lexigram.ai.prompt.service.service import PromptService
from lexigram.hooks import HookRegistry


class RecordingObserver:
    """Minimal PromptObserverProtocol implementation that records calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, RenderFormat]] = []

    def on_render(
        self,
        name: str,
        version: str,
        variables: dict[str, object],
        rendered_output: str,
        render_format: RenderFormat,
    ) -> None:
        self.calls.append((name, version, render_format))


def _tmpl(content: str = "Hello, {name}!") -> PromptTemplate:
    return PromptTemplate(
        name="t",
        version="v1",
        content=content,
        required_variables=("name",),
    )


def _render_and_settle(service: PromptService) -> None:
    async def _run() -> None:
        service.render(PromptRenderRequest(name="t", variables={"name": "Alice"}))
        await asyncio.sleep(0)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Observer receives the render format
# ---------------------------------------------------------------------------


def test_observer_receives_render_format() -> None:
    observer = RecordingObserver()
    svc = PromptService([_tmpl()], observer=observer)

    svc.render(PromptRenderRequest(name="t", variables={"name": "Alice"}))

    assert observer.calls == [("t", "v1", RenderFormat.F_STRING)]


def test_observer_reports_jinja2_format() -> None:
    pytest.importorskip("jinja2")
    observer = RecordingObserver()
    tmpl = _tmpl(content="{{ name }}")
    object.__setattr__(tmpl, "format", RenderFormat.JINJA2)
    svc = PromptService([tmpl], observer=observer)

    svc.render(PromptRenderRequest(name="t", variables={"name": "Alice"}))

    assert observer.calls[0][2] == RenderFormat.JINJA2


def test_noop_observer_accepts_format() -> None:
    svc = PromptService([_tmpl()], observer=NoOpPromptObserver())
    svc.render(PromptRenderRequest(name="t", variables={"name": "Alice"}))


def test_observer_is_protocol_conformant() -> None:
    assert isinstance(RecordingObserver(), PromptObserverProtocol)


# ---------------------------------------------------------------------------
# Hook emission through the framework HookRegistry
# ---------------------------------------------------------------------------


def test_rendered_hook_emitted_with_format() -> None:
    hooks = HookRegistry("prompt-test")
    received: list[PromptRenderedHook] = []
    hooks.register_action(
        "prompt.rendered",
        lambda **kwargs: received.append(kwargs["payload"]),
    )
    svc = PromptService([_tmpl()], hook_registry=hooks)

    _render_and_settle(svc)

    assert len(received) == 1
    assert isinstance(received[0], PromptRenderedHook)
    assert received[0].render_format == RenderFormat.F_STRING


def test_template_resolved_hook_emitted() -> None:
    hooks = HookRegistry("prompt-test")
    received: list[PromptTemplateResolvedHook] = []
    hooks.register_action(
        "prompt.template_resolved",
        lambda **kwargs: received.append(kwargs["payload"]),
    )
    svc = PromptService([_tmpl()], hook_registry=hooks)

    _render_and_settle(svc)

    assert len(received) == 1
    assert isinstance(received[0], PromptTemplateResolvedHook)
    assert received[0].template_name == "t"


def test_both_hooks_fire_on_render() -> None:
    hooks = HookRegistry("prompt-test")
    fired: list[str] = []
    hooks.register_action("prompt.rendered", lambda **kwargs: fired.append("rendered"))
    hooks.register_action(
        "prompt.template_resolved", lambda **kwargs: fired.append("resolved")
    )
    svc = PromptService([_tmpl()], hook_registry=hooks)

    _render_and_settle(svc)

    assert fired == ["resolved", "rendered"]


def test_render_without_running_loop_skips_hooks() -> None:
    hooks = HookRegistry("prompt-test")
    fired: list[str] = []
    hooks.register_action("prompt.rendered", lambda **kwargs: fired.append("rendered"))
    svc = PromptService([_tmpl()], hook_registry=hooks)

    svc.render(PromptRenderRequest(name="t", variables={"name": "Alice"}))

    assert fired == []


def test_render_without_registry_is_safe() -> None:
    svc = PromptService([_tmpl()])
    _render_and_settle(svc)


def test_attach_hook_registry_wires_emission() -> None:
    hooks = HookRegistry("prompt-test")
    received: list[PromptRenderedHook] = []
    hooks.register_action(
        "prompt.rendered",
        lambda **kwargs: received.append(kwargs["payload"]),
    )
    svc = PromptService([_tmpl()])
    svc.attach_hook_registry(hooks)

    _render_and_settle(svc)

    assert len(received) == 1


# ---------------------------------------------------------------------------
# Input sanitization hook
# ---------------------------------------------------------------------------


def test_input_sanitized_hook_fires_when_sanitizer_attached() -> None:
    hooks = HookRegistry("prompt-test")
    received: list[PromptInputSanitizedHook] = []
    hooks.register_action(
        "prompt.input_sanitized",
        lambda **kwargs: received.append(kwargs["payload"]),
    )
    svc = PromptService(
        [_tmpl()],
        hook_registry=hooks,
        sanitizer=InputSanitizer(strict=True),
    )

    _render_and_settle(svc)

    assert len(received) == 1
    assert isinstance(received[0], PromptInputSanitizedHook)


def test_input_sanitized_hook_not_fired_without_sanitizer() -> None:
    hooks = HookRegistry("prompt-test")
    received: list[PromptInputSanitizedHook] = []
    hooks.register_action(
        "prompt.input_sanitized",
        lambda **kwargs: received.append(kwargs["payload"]),
    )
    svc = PromptService([_tmpl()], hook_registry=hooks)

    _render_and_settle(svc)

    assert received == []
