"""Web middleware protocols."""

from __future__ import annotations

from lexigram.contracts.web.guard import GuardProtocol
from lexigram.contracts.web.middleware.protocols import ASGIMiddlewareProtocol
from lexigram.contracts.web.middleware.registry_protocol import (
    MiddlewareRegistryProtocol,
)

__all__ = ["ASGIMiddlewareProtocol", "GuardProtocol", "MiddlewareRegistryProtocol"]
