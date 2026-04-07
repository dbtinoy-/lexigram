"""Integration helpers for lexigram-sql.

Use :class:`~lexigram.sql.config.DatabaseConfig` directly — it auto-loads
from ``LEX_DB__*`` environment variables via Pydantic's ``model_config``.
"""

from __future__ import annotations

from lexigram.sql.di.provider import DatabaseProvider
from lexigram.sql.module import DatabaseModule

__all__ = ["DatabaseModule", "DatabaseProvider"]
