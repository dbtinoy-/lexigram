"""Relay request-log storage and usage read services.

Persistence of redaction-safe dispatch entries from the relay gateway
and aggregation into daily usage and model rankings.

Exports:
    - ``SqlRelayRequestLogStore``: SQL-backed request-log sink.
    - ``RelayUsageService``: aggregate reads over the request logs.
"""

from lexigram.ai.governance.relay_logs.persistence import (
    SqlRelayRequestLogStore,
)
from lexigram.ai.governance.relay_logs.service import RelayUsageService

__all__ = ["RelayUsageService", "SqlRelayRequestLogStore"]
