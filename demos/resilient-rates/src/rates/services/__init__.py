"""Service layer for the resilient rates demo.

Convention followed: **Service pattern** — ``RatesService`` is the primary
service, resolved via the container as a singleton.  It owns the
cache-aside read path, resilience pipeline configuration, and stale tier
management.

Exports:

- ``RatesService`` — the main service class
- ``ServiceStats`` — aggregate counters for observability
"""

from __future__ import annotations

from rates.services.rates_service import RatesService, ServiceStats

__all__ = ["RatesService", "ServiceStats"]
