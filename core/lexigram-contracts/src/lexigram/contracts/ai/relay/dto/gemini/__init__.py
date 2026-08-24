"""Gemini ``generateContent`` wire DTO family.

Field names follow the Gemini API camelCase wire format; the DTO layer
accepts documented snake_case aliases only where noted.
"""

from __future__ import annotations

from lexigram.contracts.ai.relay.dto.gemini.content import (
    GeminiContent as GeminiContent,
)
from lexigram.contracts.ai.relay.dto.gemini.content import GeminiPart as GeminiPart
from lexigram.contracts.ai.relay.dto.gemini.request import (
    GeminiRequest as GeminiRequest,
)
from lexigram.contracts.ai.relay.dto.gemini.response import (
    GeminiCandidate as GeminiCandidate,
)
from lexigram.contracts.ai.relay.dto.gemini.response import (
    GeminiGroundingMetadata as GeminiGroundingMetadata,
)
from lexigram.contracts.ai.relay.dto.gemini.response import (
    GeminiPromptFeedback as GeminiPromptFeedback,
)
from lexigram.contracts.ai.relay.dto.gemini.response import (
    GeminiResponse as GeminiResponse,
)
from lexigram.contracts.ai.relay.dto.gemini.response import (
    GeminiSafetyRating as GeminiSafetyRating,
)
from lexigram.contracts.ai.relay.dto.gemini.response import (
    GeminiUsageMetadata as GeminiUsageMetadata,
)

__all__ = [
    "GeminiCandidate",
    "GeminiContent",
    "GeminiGroundingMetadata",
    "GeminiPart",
    "GeminiPromptFeedback",
    "GeminiRequest",
    "GeminiResponse",
    "GeminiSafetyRating",
    "GeminiUsageMetadata",
]
