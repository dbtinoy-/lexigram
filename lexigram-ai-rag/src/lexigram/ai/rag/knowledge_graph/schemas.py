from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False)
class ExtractionResult(DomainModel):
    text: str
    entities: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
