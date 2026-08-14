"""Admin DI package."""

from __future__ import annotations

from lexigram.admin.di.bundle_provider import AdminProvider
from lexigram.admin.module import AdminModule

__all__ = ["AdminModule", "AdminProvider"]
