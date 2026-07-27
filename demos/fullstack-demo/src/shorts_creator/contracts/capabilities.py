from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import Any


class CapabilityVocabularyError(ValueError):
    """Raised when a declared capability name is not in the closed vocabulary."""

    def __init__(self, kind: str, name: str, valid: Sequence[str]):
        self.kind = kind
        self.name = name
        self.valid = list(valid)
        super().__init__(
            f"unknown {kind} capability {name!r}; valid names: {', '.join(sorted(valid))}"
        )


class ScriptCapability(str, Enum):
    HOOK = "hook"
    PROBLEM = "problem"
    PRINCIPLE = "principle"
    PRACTICE = "practice"
    REFLECTION = "reflection"
    MESSAGE = "message"
    CONTEXT = "context"
    EXPLANATION = "explanation"
    APPLICATION = "application"
    METAPHOR = "metaphor"
    CONCLUSION = "conclusion"
    MESSAGE_LINES = "message_lines"
    CLOSING = "closing"
    TOP_ITEMS = "top_items"
    CLAIM = "claim"
    FACT = "fact"
    TWIST = "twist"


class VoiceCapability(str, Enum):
    TTS_STORY = "tts_story"


class PipelineCapabilityName(str, Enum):
    WORD_TIMING = "word_timing"
    CAPTIONS = "captions"
    BACKGROUND = "background"
    OUTRO = "outro"
    TTS_STORY = "tts_story"
    MUSIC_BEAT = "music_beat"
    RANKED_SCREENS = "ranked_screens"


class AssetRole(str, Enum):
    MUSIC = "music"
    FONT = "font"
    WATERMARK = "watermark"
    BG_CLIP = "bg_clip"
    OUTRO_CLIP = "outro_clip"


_VOCABULARY: dict[str, frozenset[str]] = {
    "script": frozenset(c.value for c in ScriptCapability),
    "voice": frozenset(c.value for c in VoiceCapability),
    "pipeline": frozenset(c.value for c in PipelineCapabilityName),
    "assets": frozenset(c.value for c in AssetRole),
}


def parse_capabilities(raw: Any, kind: str) -> list[str]:
    """Validate + normalize a raw capability list against the closed vocabulary.

    Raises ``CapabilityVocabularyError`` on the first unknown name with the
    list of valid names; normalizes whitespace and dedupes.
    """
    vocab = _VOCABULARY[kind]
    names: list[str] = []
    for item in raw or []:
        name = str(item).strip()
        if name not in vocab:
            raise CapabilityVocabularyError(kind, name, sorted(vocab))
        if name not in names:
            names.append(name)
    return names
