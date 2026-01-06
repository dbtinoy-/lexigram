"""Setting models for lexigram-admin."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SystemSetting:
    """System setting model."""

    key: str
    value: str
    scope: str = "global"
    scope_id: str = "system"
    type: str = "string"
    is_sensitive: bool = False
    updated_at: datetime | None = None
    updated_by: str | None = None
    id: int | None = None
