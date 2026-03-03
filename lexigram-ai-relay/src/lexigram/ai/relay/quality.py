"""Route quality matrix for the relay conversion engine.

Quality values mirror relaykit and describe semantic closeness between
two wire protocols, not test confidence.  Every directed pair has one
stable value; same-format conversion is always :data:`ConversionQuality.GOOD`.
"""

from __future__ import annotations

from lexigram.contracts.ai.relay.types import ConversionQuality, RelayFormat

__all__ = ["ROUTE_QUALITY", "route_quality"]


ROUTE_QUALITY: dict[tuple[RelayFormat, RelayFormat], ConversionQuality] = {
    (RelayFormat.OPENAI_CHAT, RelayFormat.OPENAI_RESPONSES): ConversionQuality.GOOD,
    (RelayFormat.OPENAI_RESPONSES, RelayFormat.OPENAI_CHAT): ConversionQuality.GOOD,
    (RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE): ConversionQuality.FAIR,
    (RelayFormat.OPENAI_CHAT, RelayFormat.GEMINI): ConversionQuality.FAIR,
    (RelayFormat.OPENAI_RESPONSES, RelayFormat.CLAUDE): ConversionQuality.FAIR,
    (RelayFormat.OPENAI_RESPONSES, RelayFormat.GEMINI): ConversionQuality.FAIR,
    (RelayFormat.CLAUDE, RelayFormat.OPENAI_CHAT): ConversionQuality.FAIR,
    (RelayFormat.CLAUDE, RelayFormat.OPENAI_RESPONSES): ConversionQuality.FAIR,
    (RelayFormat.GEMINI, RelayFormat.OPENAI_CHAT): ConversionQuality.FAIR,
    (RelayFormat.GEMINI, RelayFormat.OPENAI_RESPONSES): ConversionQuality.FAIR,
    (RelayFormat.CLAUDE, RelayFormat.GEMINI): ConversionQuality.DISCOURAGED,
    (RelayFormat.GEMINI, RelayFormat.CLAUDE): ConversionQuality.DISCOURAGED,
}
"""Stable quality for every directed pair, keyed by ``(source, target)``."""


def route_quality(source: RelayFormat, target: RelayFormat) -> ConversionQuality:
    """Return the semantic-closeness quality for a directed pair.

    Args:
        source: Source wire format.
        target: Target wire format.

    Returns:
        :data:`ConversionQuality.GOOD` for same-format conversion and for
        routes without a configured quality, otherwise the configured
        matrix value.
    """
    if source is target:
        return ConversionQuality.GOOD
    return ROUTE_QUALITY.get((source, target), ConversionQuality.DISCOURAGED)
