"""Topic restrictor input guard.

Blocks or warns on inputs that touch topics declared off-limits for
a deployment.  Matching uses exact keyword/phrase lookup and optional
word-boundary enforcement — no external API calls.

For more accurate topic classification use an LLM-based classifier as
a second guard in the pipeline after this fast pre-filter.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from lexigram.ai.guard.input.base import AbstractInputGuard
from lexigram.ai.guard.pipeline.result import GuardCheckResult
from lexigram.contracts.ai.guards import GuardResultProtocol
from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.ai.exceptions import GuardError


def _build_pattern(topic: str, whole_word: bool) -> re.Pattern[str]:
    """Compile a regex pattern for a topic phrase.

    Args:
        topic: The topic phrase to match.
        whole_word: Whether to require word boundaries around the match.

    Returns:
        Compiled regex pattern.
    """
    escaped = re.escape(topic)
    if whole_word:
        return re.compile(r"\b" + escaped + r"\b", re.I)
    return re.compile(escaped, re.I)


class TopicRestrictor(AbstractInputGuard):
    """Input guard that blocks prohibited topics.

    Args:
        restricted_topics: List of topic keywords/phrases to prohibit.
        action: Action when a restricted topic is found —
                ``"block"`` (default) or ``"warn"``.
        whole_word: If ``True`` (default), only match whole words /
                    phrase boundaries to reduce false positives.

    Example::

        guard = TopicRestrictor(
            restricted_topics=["weapons", "explosives", "self-harm"],
            action="block",
        )
        result = await guard.check(user_message)
    """

    def __init__(
        self,
        restricted_topics: list[str],
        action: str = "block",
        whole_word: bool = True,
    ) -> None:
        """Initialise the topic restrictor.

        Args:
            restricted_topics: List of prohibited topic keywords/phrases.
            action: ``"block"`` or ``"warn"``.
            whole_word: Enforce word boundaries on matches.
        """
        super().__init__(action=action)
        self._patterns: list[tuple[str, re.Pattern[str]]] = [
            (topic, _build_pattern(topic, whole_word)) for topic in restricted_topics
        ]

    async def check(
        self,
        content: str,
        *,
        messages: list[Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Result[GuardResultProtocol, GuardError]:
        """Check content against restricted topics.

        Args:
            content: Input text to evaluate.
            messages: Unused — present for protocol compatibility.
            metadata: Optional metadata.

        Returns:
            PASS if no restricted topics found; BLOCK or WARN otherwise.
        """
        matched_topics: list[str] = []
        for topic, pattern in self._patterns:
            if pattern.search(content):
                matched_topics.append(topic)

        if not matched_topics:
            return Ok(GuardCheckResult.allow(self.name))

        if self._action == "warn":
            return Ok(
                GuardCheckResult.warn(
                    self.name,
                    reason=f"Restricted topics mentioned: {', '.join(matched_topics)}",
                    matched_topics=matched_topics,
                )
            )

        return Ok(
            GuardCheckResult.block(
                self.name,
                reason=f"Input mentions restricted topics: {', '.join(matched_topics)}",
                matched_topics=matched_topics,
            )
        )


__all__ = ["TopicRestrictor"]
