from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FindingRecord:
    """Structured record for a single audit finding."""

    key: str
    status: str
    source: str
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AuditReport:
    """Canonical metadata and findings for a generated audit report."""

    name: str
    title: str
    generated_at: str
    output_markdown: str
    output_json: str
    records: list[FindingRecord]
