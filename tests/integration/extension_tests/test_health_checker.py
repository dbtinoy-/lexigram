"""Tests verifying health checker category filtering."""

from __future__ import annotations

import pytest

from lexigram.monitor.health import (
    HealthCheckCategory,
    HealthChecker,
    HealthStatus,
)


@pytest.mark.asyncio
async def test_run_liveness_and_readiness():
    checker = HealthChecker()

    # simple boolean checks
    checker.add("live", lambda: True, category=HealthCheckCategory.LIVENESS)
    checker.add(
        "ready",
        lambda: False,
        category=HealthCheckCategory.READINESS,
    )
    checker.add(
        "startup",
        lambda: True,
        category=HealthCheckCategory.STARTUP,
    )

    status_live, results_live = await checker.run_liveness()

    # run_liveness should only look at "live" check
    assert status_live == HealthStatus.HEALTHY
    assert "live" in results_live
    assert len(results_live) == 1


@pytest.mark.asyncio
async def test_run_readiness_and_startup():
    checker = HealthChecker()
    checker.add("a", lambda: True, category=HealthCheckCategory.READINESS)
    checker.add("b", lambda: True, category=HealthCheckCategory.STARTUP)
    status_read, _ = await checker.run_readiness()
    assert status_read == HealthStatus.HEALTHY
    status_start, _ = await checker.run_startup()
    assert status_start == HealthStatus.HEALTHY
