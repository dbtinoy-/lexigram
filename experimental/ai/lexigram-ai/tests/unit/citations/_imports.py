"""Tests for citation and source tracking."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.citations.core import (
    Citation,
    CitationStyle,
    CitationTracker,
    CitedResponse,
    Source,
    SourceType,
)
