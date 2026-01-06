"""Management overview page for /admin/tasks."""

from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.logging import get_logger
from lexigram.tasks import TaskScheduler
from lexigram.tasks.execution.metrics import TaskMetricsCollector
from lexigram.ui import Card, Divider, Grid, StatCard, el, render_to_string

logger = get_logger(__name__)


class TasksOverviewPage:
    """Management overview for /admin/tasks."""

    def __init__(
        self,
        scheduler: TaskScheduler | None = None,
        metrics_collector: TaskMetricsCollector | None = None,
    ) -> None:
        self._scheduler = scheduler
        self._metrics_collector = metrics_collector

    async def handle(self, request: Any) -> HTMLResponse:
        """Handle request and render overview page."""
        running = 0
        completed = 0
        failed = 0
        avg_duration_ns = 0
        max_concurrency = "N/A"
        queue_size = "N/A"
        worker_count = "N/A"
        scheduler_status = "N/A"

        try:
            if self._scheduler is not None:
                running = getattr(self._scheduler, "running_count", 0)
                completed = getattr(self._scheduler, "completed_count", 0)
                failed = getattr(self._scheduler, "failed_count", 0)
                max_concurrency = str(
                    getattr(self._scheduler, "max_concurrency", "N/A")
                )
                queue_size = str(getattr(self._scheduler, "queue_size", "N/A"))
                worker_count = str(getattr(self._scheduler, "worker_count", "N/A"))
                scheduler_status = str(getattr(self._scheduler, "status", "N/A"))
        except Exception as exc:
            logger.warning("tasks_overview.scheduler_unavailable", error=str(exc))

        try:
            if self._metrics_collector is not None:
                avg_duration_ns = getattr(
                    self._metrics_collector, "average_duration_ns", 0
                )
        except Exception as exc:
            logger.warning("tasks_overview.metrics_unavailable", error=str(exc))

        avg_ms = int(avg_duration_ns / 1_000_000) if avg_duration_ns else 0

        html = render_to_string(
            el(
                "div",
                el("h1", "Tasks", class_="text-2xl font-bold text-[var(--foreground)]"),
                el(
                    "p",
                    "Background task scheduling, execution, and monitoring.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(label="Running", value=str(running), icon="play-circle"),
                    StatCard(
                        label="Completed", value=str(completed), icon="check-circle"
                    ),
                    StatCard(label="Failed", value=str(failed), icon="x-circle"),
                    StatCard(label="Avg Duration", value=f"{avg_ms}ms", icon="clock"),
                    cols={"default": 1, "lg": 4},
                    gap=4,
                    class_="mb-6 mt-6",
                ),
                Card(
                    title="Task Scheduler",
                    content=render_to_string(
                        el(
                            "dl",
                            el(
                                "dt",
                                "Max Concurrency",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                max_concurrency,
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Queue Size",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                queue_size,
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Worker Count",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                worker_count,
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Status",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                scheduler_status,
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            class_="divide-y divide-[var(--border)]",
                        )
                    ),
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
