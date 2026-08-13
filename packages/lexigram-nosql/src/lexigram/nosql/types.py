"""Type aliases for NoSQL operations."""

from __future__ import annotations

from typing import Any

# Document types
DocumentDict = dict[str, Any]
FilterDict = dict[str, Any]
UpdateDict = dict[str, Any]
ProjectionDict = dict[str, Any]
SortSpec = list[tuple[str, int]]
PipelineStage = dict[str, Any]
Pipeline = list[PipelineStage]
