"""Speculative execution module — draft-verify pattern and tool pre-fetching."""

from __future__ import annotations

from lexigram.ai.agents.speculation.draft_verify import DraftVerifyExecutor
from lexigram.ai.agents.speculation.predictor import KeywordToolCallPredictor
from lexigram.ai.agents.speculation.prefetcher import SpeculativeToolPreFetcher
from lexigram.ai.agents.speculation.protocols import ToolCallPredictorProtocol

__all__ = [
    "DraftVerifyExecutor",
    "KeywordToolCallPredictor",
    "SpeculativeToolPreFetcher",
    "ToolCallPredictorProtocol",
]
