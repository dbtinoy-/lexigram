"""Unified Health Check System."""

from __future__ import annotations

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.contracts.core.health import HealthCheckCategory
from lexigram.monitor.health.base import HealthCheck
from lexigram.monitor.health.cached import CachedHealthChecker
from lexigram.monitor.health.checker import HealthChecker, health_checker
from lexigram.monitor.health.checker_registry import HealthCheckerRegistry
from lexigram.monitor.health.functions import FunctionHealthCheck
from lexigram.monitor.health.registry import HealthCheckRegistry

__all__ = [
    "CachedHealthChecker",
    "FunctionHealthCheck",
    "HealthCheck",
    "HealthCheckCategory",
    "HealthCheckRegistry",
    "HealthCheckResult",
    "HealthChecker",
    "HealthCheckerRegistry",
    "HealthStatus",
    "health_checker",
]
