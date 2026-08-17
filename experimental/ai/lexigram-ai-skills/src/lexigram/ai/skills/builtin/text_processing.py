"""TextProcessingSkill — text summarisation and translation stubs."""

from __future__ import annotations

from typing import Any

from lexigram.ai.skills.base import BaseSkill
from lexigram.contracts.ai.skills import SkillDefinition, SkillError, SkillResult
from lexigram.result import Ok, Result


class TextSummarizeSkill(BaseSkill):
    """Return a simple extractive summary of the provided text.

    This built-in provides a deterministic word-count truncation summary.
    For production use, replace or extend with an LLM-backed implementation.

    Example output::

        {"summary": "First 50 words of the input...", "word_count": 200}
    """

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition.

        Returns:
            SkillDefinition for the text_summarize skill.
        """
        return SkillDefinition(
            name="text_summarize",
            description=(
                "Produce a brief summary of the provided text. "
                "Uses extractive truncation by default."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to summarise.",
                    },
                    "max_words": {
                        "type": "integer",
                        "description": "Maximum words in the summary. Defaults to 50.",
                        "default": 50,
                    },
                },
                "required": ["text"],
            },
            category="text",
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Summarise *text* by truncating to *max_words*.

        Args:
            **kwargs: Requires ``text`` (str); accepts ``max_words`` (int).

        Returns:
            Ok result with ``summary`` and ``word_count`` keys.
        """
        text: str = kwargs.get("text", "")
        max_words: int = int(kwargs.get("max_words", 50))

        words = text.split()
        total = len(words)
        summary = " ".join(words[:max_words])
        if total > max_words:
            summary += "..."

        return Ok(
            SkillResult(
                skill_name="text_summarize",
                success=True,
                output={"summary": summary, "word_count": total},
            )
        )


class TextTranslateSkill(BaseSkill):
    """Stub skill that echoes text with a language annotation.

    Replace with an LLM or translation API backend for real translations.

    Example output::

        {"translated": "...", "source_language": "auto", "target_language": "es"}
    """

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition.

        Returns:
            SkillDefinition for the text_translate skill.
        """
        return SkillDefinition(
            name="text_translate",
            description=(
                "Translate text to the specified target language. "
                "(Stub — echoes input; integrate an LLM or translation API.)"
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to translate.",
                    },
                    "target_language": {
                        "type": "string",
                        "description": "BCP-47 language tag (e.g. 'es', 'fr', 'de').",
                    },
                    "source_language": {
                        "type": "string",
                        "description": "Source language tag. Defaults to 'auto'.",
                        "default": "auto",
                    },
                },
                "required": ["text", "target_language"],
            },
            category="text",
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Return the input text unchanged with metadata (stub).

        Args:
            **kwargs: Requires ``text`` and ``target_language``; accepts
                ``source_language``.

        Returns:
            Ok result with ``translated``, ``source_language``, and
            ``target_language`` keys.
        """
        text: str = kwargs.get("text", "")
        target: str = kwargs.get("target_language", "en")
        source: str = kwargs.get("source_language", "auto")

        return Ok(
            SkillResult(
                skill_name="text_translate",
                success=True,
                output={
                    "translated": text,  # stub: return unchanged
                    "source_language": source,
                    "target_language": target,
                },
            )
        )
