"""Controllers module for Lexigram Admin."""

from __future__ import annotations

from lexigram.admin.controllers.auth import AuthController
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.controllers.dashboard import DashboardController
from lexigram.admin.controllers.search import SearchController
from lexigram.admin.controllers.settings import SettingsController
from lexigram.admin.controllers.setup import SetupController
from lexigram.admin.controllers.widgets import WidgetController

__all__ = [
    "AdminController",
    "AuthController",
    "DashboardController",
    "SearchController",
    "SettingsController",
    "SetupController",
    "WidgetController",
]
