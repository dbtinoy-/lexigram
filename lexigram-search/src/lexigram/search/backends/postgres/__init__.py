"""PostgreSQL-backed search backend exports."""

from __future__ import annotations

from lexigram.search.backends.postgres.backend import PostgresDatabaseSearchBackend

__all__ = ["PostgresDatabaseSearchBackend"]
