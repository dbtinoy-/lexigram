"""
Preprocessed document result class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from lexigram.ai.rag.preprocessing.types import ExtractedImage, ExtractedTable


@dataclass
class PreprocessedDocument:
    """Result of document preprocessing.

    Attributes:
        content: Main text content.
        metadata: Document metadata.
        raw_content: Original raw content.
        preprocessing_stats: Statistics about preprocessing.
    """

    content: str = ""
    metadata: Any = None
    raw_content: str | None = None
    preprocessing_stats: dict[str, Any] = field(default_factory=dict)
    text: str = ""
    images: list[ExtractedImage] = field(default_factory=list)
    tables: list[ExtractedTable] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    processing_time: float | None = None

    def __post_init__(self) -> Any:
        if self.text and not self.content:
            self.content = self.text
        if self.content and not self.text:
            self.text = self.content
