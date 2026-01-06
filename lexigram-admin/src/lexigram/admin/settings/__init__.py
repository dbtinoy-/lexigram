"""Admin settings package."""

from __future__ import annotations

from lexigram.admin.settings.loader import AdminConfigLoader
from lexigram.admin.settings.settings import AdminSettings, get_admin_settings

__all__ = ["AdminConfigLoader", "AdminSettings", "get_admin_settings"]
