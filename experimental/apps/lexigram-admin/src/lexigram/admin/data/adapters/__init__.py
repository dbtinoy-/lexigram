"""Data source adapters for Lexigram Admin."""

from __future__ import annotations

from lexigram.admin.data.adapters.api_adapter import APIDataSource
from lexigram.admin.data.adapters.memory_adapter import InMemoryDataSource
from lexigram.admin.data.adapters.repository import RepositoryDataSource

__all__ = [
    "APIDataSource",
    "InMemoryDataSource",
    "RepositoryDataSource",
]
