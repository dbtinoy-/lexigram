"""Management pages for lexigram-tasks admin."""

from __future__ import annotations

from lexigram.tasks.admin.pages.active import TasksActivePage
from lexigram.tasks.admin.pages.failed import TasksFailedPage
from lexigram.tasks.admin.pages.history import TasksHistoryPage
from lexigram.tasks.admin.pages.overview import TasksOverviewPage

__all__ = [
    "TasksActivePage",
    "TasksFailedPage",
    "TasksHistoryPage",
    "TasksOverviewPage",
]
