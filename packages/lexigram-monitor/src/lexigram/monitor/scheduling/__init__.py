"""Periodic scheduled-worker base for lexigram.monitor.

Implements the shared scheduled-worker pattern against the contracts
:class:`~lexigram.contracts.infra.tasks.TaskManagerProtocol` so monitor
never imports ``lexigram.tasks`` directly.
"""

from __future__ import annotations

from lexigram.monitor.scheduling.scheduled_worker import MonitorScheduledWorker

__all__ = ["MonitorScheduledWorker"]
