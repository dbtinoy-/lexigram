"""Focused tests for the moderation overview admin page."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lexigram.ai.guard.admin.pages.overview import ModerationOverviewPage
from lexigram.ai.guard.config import GuardConfig
from lexigram.contracts.admin import PageContent
from lexigram.contracts.admin.widget_content import EmptyContent, Stat, StatContent


class _FakeRequest:
    pass


def _pipeline(inputs: int = 0, outputs: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        _input_guards=[
            SimpleNamespace(name=f"i{n}", _action="reject") for n in range(inputs)
        ],
        _output_guards=[
            SimpleNamespace(name=f"o{n}", _action="redact") for n in range(outputs)
        ],
    )


def _stats(content: PageContent) -> dict[str, Stat]:
    assert isinstance(content.body, StatContent)
    return {s.label: s for s in content.body.stats}


class TestModerationOverviewPage:
    @pytest.mark.asyncio
    async def test_unavailable_when_no_dependencies(self) -> None:
        content = await ModerationOverviewPage().handle(_FakeRequest())
        assert content.title == "Moderation"
        assert isinstance(content.body, EmptyContent)
        assert content.body.title == "Moderation Unavailable"
        assert content.body.message == "The guard pipeline could not be resolved."
        assert content.body.icon == "shield"

    @pytest.mark.asyncio
    async def test_disabled_without_config(self) -> None:
        content = await ModerationOverviewPage(pipeline=_pipeline(1, 1)).handle(
            _FakeRequest()
        )
        stats = _stats(content)
        assert stats["Status"].value == "Disabled"
        assert stats["Status"].icon == "shield-off"
        assert stats["Input Guards"].value == "1"
        assert stats["Output Guards"].value == "1"

    @pytest.mark.asyncio
    async def test_active_when_enabled(self) -> None:
        page = ModerationOverviewPage(
            pipeline=_pipeline(2, 3),
            config=GuardConfig(enabled=True),
        )
        content = await page.handle(_FakeRequest())
        stats = _stats(content)
        assert stats["Status"].value == "Active"
        assert stats["Status"].icon == "shield-check"
        assert stats["Input Guards"].value == "2"
        assert stats["Input Guards"].icon == "log-in"
        assert stats["Output Guards"].value == "3"
        assert stats["Output Guards"].icon == "log-out"
