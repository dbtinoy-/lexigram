"""Response synthesizers package.

This package provides various strategies for synthesizing responses from
retrieved context chunks.
"""

from __future__ import annotations

from lexigram.ai.rag.synthesis.synthesizers.abstractive import (
    AbstractiveSynthesizer,
)
from lexigram.ai.rag.synthesis.synthesizers.base import (
    AbstractSynthesizer,
    ResponseSynthesizerProtocol,
)
from lexigram.ai.rag.synthesis.synthesizers.direct import DirectSynthesizer
from lexigram.ai.rag.synthesis.synthesizers.extractive import (
    ExtractiveSynthesizer,
)
from lexigram.ai.rag.synthesis.synthesizers.hybrid import HybridSynthesizer

__all__ = [
    "AbstractSynthesizer",
    "AbstractiveSynthesizer",
    "DirectSynthesizer",
    "ExtractiveSynthesizer",
    "HybridSynthesizer",
    "ResponseSynthesizerProtocol",
]
