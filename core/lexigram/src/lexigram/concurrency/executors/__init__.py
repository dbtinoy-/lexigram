"""Task execution primitives: dispatcher, parallel execution, task manager."""

from __future__ import annotations

from lexigram.concurrency.executors.dispatcher import DispatcherImpl
from lexigram.concurrency.executors.task_manager import TaskManager

__all__ = ["DispatcherImpl", "TaskManager"]
