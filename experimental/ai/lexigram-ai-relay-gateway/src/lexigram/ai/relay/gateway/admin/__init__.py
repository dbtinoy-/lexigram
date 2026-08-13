"""Relay gateway admin surfaces.

The contributor registers dashboards for channel health, route metrics,
active streams, and runtime policy, plus permissioned control actions.
"""

from __future__ import annotations

from lexigram.ai.relay.gateway.admin.contributor import (
    RelayGatewayAdminContributor,
)

__all__ = ["RelayGatewayAdminContributor"]
