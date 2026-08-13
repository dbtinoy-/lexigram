"""Tests for TextSummarizeSkill and TextTranslateSkill."""

from __future__ import annotations

import pytest

from lexigram.ai.skills.builtin.text_processing import (
    TextSummarizeSkill,
    TextTranslateSkill,
)


class TestTextSummarizeSkill:
    """Tests for the text_summarize built-in skill."""

    @pytest.mark.asyncio
    async def test_short_text_returned_verbatim(self) -> None:
        skill = TextSummarizeSkill()
        text = "Hello world"
        result = await skill.execute(text=text, max_words=50)
        assert result.is_ok()
        output = result.unwrap().output
        assert output["summary"] == text
        assert output["word_count"] == 2

    @pytest.mark.asyncio
    async def test_long_text_truncated_with_ellipsis(self) -> None:
        skill = TextSummarizeSkill()
        text = " ".join(["word"] * 100)
        result = await skill.execute(text=text, max_words=10)
        assert result.is_ok()
        summary = result.unwrap().output["summary"]
        assert summary.endswith("...")
        assert len(summary.replace("...", "").split()) == 10

    @pytest.mark.asyncio
    async def test_word_count_reflects_original_length(self) -> None:
        skill = TextSummarizeSkill()
        words = ["a"] * 200
        result = await skill.execute(text=" ".join(words), max_words=50)
        assert result.unwrap().output["word_count"] == 200

    @pytest.mark.asyncio
    async def test_default_max_words_is_50(self) -> None:
        skill = TextSummarizeSkill()
        text = " ".join(["x"] * 100)
        result = await skill.execute(text=text)
        summary_words = result.unwrap().output["summary"].replace("...", "").strip().split()
        assert len(summary_words) == 50

    def test_definition_name(self) -> None:
        assert TextSummarizeSkill().definition.name == "text_summarize"


class TestTextTranslateSkill:
    """Tests for the text_translate built-in skill (stub)."""

    @pytest.mark.asyncio
    async def test_returns_input_unchanged(self) -> None:
        skill = TextTranslateSkill()
        result = await skill.execute(text="Hello", target_language="es")
        assert result.is_ok()
        output = result.unwrap().output
        assert output["translated"] == "Hello"

    @pytest.mark.asyncio
    async def test_target_language_forwarded(self) -> None:
        skill = TextTranslateSkill()
        result = await skill.execute(text="Hi", target_language="fr")
        assert result.unwrap().output["target_language"] == "fr"

    @pytest.mark.asyncio
    async def test_default_source_is_auto(self) -> None:
        skill = TextTranslateSkill()
        result = await skill.execute(text="Hi", target_language="de")
        assert result.unwrap().output["source_language"] == "auto"

    def test_definition_name(self) -> None:
        assert TextTranslateSkill().definition.name == "text_translate"
