"""Optional-dependency availability shims shared by sqlite backend modules."""

from typing import Any

# Declare optional third-party/runtime names as Any so we can provide runtime fallbacks
aiosqlite: Any = None
try:
    import aiosqlite

    HAS_SQLITE = True
except ImportError:
    HAS_SQLITE = False


from lexigram.contracts import (
    HealthCheckResult,
    HealthStatus,
    RetryConfig,
)
from lexigram.contracts.infra.resilience import CircuitBreakerProtocol
from lexigram.sql.lib.retry import retry_call

HAS_MONITORING = False
try:
    from lexigram.sql.monitoring import DatabaseMonitor as _RealDatabaseMonitor

    DatabaseMonitor = _RealDatabaseMonitor
    HAS_MONITORING = True
except ImportError:
    HAS_MONITORING = False
    DatabaseMonitor = None  # type: ignore[assignment,misc]
