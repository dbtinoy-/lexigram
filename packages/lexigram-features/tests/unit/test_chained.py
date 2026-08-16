"""Tests for ChainedProvider — first-match-wins priority ordering."""

from __future__ import annotations

import pytest

from lexigram.features.backends.chained import ChainedProvider
from lexigram.features.backends.local import LocalProvider
from lexigram.features.types import Flag, FlagType


def _make_provider(*flags: Flag) -> LocalProvider:
    return LocalProvider({f.name: f for f in flags})


def _flag(name: str, *, enabled: bool = True) -> Flag:
    return Flag(name=name, type=FlagType.BOOLEAN, enabled=enabled)


class TestChainedProviderPriority:
    """First provider in the chain wins when multiple define the same flag."""

    @pytest.mark.asyncio
    async def test_first_provider_wins_for_get_flag_definition(self) -> None:
        high = _make_provider(_flag("feat", enabled=True))
        low = _make_provider(_flag("feat", enabled=False))
        chain = ChainedProvider([high, low])

        result = await chain.get_flag_definition("feat")
        assert result is not None
        assert result.enabled is True

    @pytest.mark.asyncio
    async def test_second_provider_used_when_first_lacks_flag(self) -> None:
        empty = LocalProvider()
        fallback = _make_provider(_flag("feat", enabled=False))
        chain = ChainedProvider([empty, fallback])

        result = await chain.get_flag_definition("feat")
        assert result is not None
        assert result.enabled is False

    @pytest.mark.asyncio
    async def test_none_returned_when_no_provider_has_flag(self) -> None:
        chain = ChainedProvider([LocalProvider(), LocalProvider()])
        assert await chain.get_flag_definition("missing") is None

    @pytest.mark.asyncio
    async def test_single_provider_chain_delegates(self) -> None:
        only_one = _make_provider(_flag("x"))
        chain = ChainedProvider([only_one])
        assert await chain.get_flag_definition("x") is not None

    @pytest.mark.asyncio
    async def test_empty_chain_returns_none(self) -> None:
        chain = ChainedProvider([])
        assert await chain.get_flag_definition("x") is None


class TestChainedProviderGetAllFlags:
    """get_all_flags() merges providers; earlier providers take precedence."""

    @pytest.mark.asyncio
    async def test_high_priority_flag_wins_on_collision(self) -> None:
        high = _make_provider(_flag("shared", enabled=True))
        low = _make_provider(_flag("shared", enabled=False))
        chain = ChainedProvider([high, low])

        flags = await chain.get_all_flags()
        assert flags["shared"].enabled is True

    @pytest.mark.asyncio
    async def test_unique_flags_from_all_providers_are_merged(self) -> None:
        p1 = _make_provider(_flag("only_in_p1"))
        p2 = _make_provider(_flag("only_in_p2"))
        chain = ChainedProvider([p1, p2])

        flags = await chain.get_all_flags()
        assert "only_in_p1" in flags
        assert "only_in_p2" in flags

    @pytest.mark.asyncio
    async def test_empty_chain_returns_empty_dict(self) -> None:
        chain = ChainedProvider([])
        assert await chain.get_all_flags() == {}

    @pytest.mark.asyncio
    async def test_three_provider_precedence(self) -> None:
        """First provider of three takes precedence over second and third."""
        p1 = _make_provider(_flag("flag", enabled=True))
        p2 = _make_provider(_flag("flag", enabled=False))
        p3 = _make_provider(_flag("flag", enabled=False))
        chain = ChainedProvider([p1, p2, p3])

        flags = await chain.get_all_flags()
        assert flags["flag"].enabled is True

    @pytest.mark.asyncio
    async def test_single_provider_all_flags_returned_unchanged(self) -> None:
        p = _make_provider(_flag("a"), _flag("b"), _flag("c"))
        chain = ChainedProvider([p])
        flags = await chain.get_all_flags()
        assert set(flags.keys()) == {"a", "b", "c"}
