"""Framework integration for lexigram-storage."""

from __future__ import annotations

from lexigram.storage.di.provider import StorageProvider
from lexigram.storage.module import StorageModule

__all__ = ["StorageModule", "StorageProvider"]
