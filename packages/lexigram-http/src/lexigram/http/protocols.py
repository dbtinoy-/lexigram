"""Re-export HTTP protocols for consumer convenience.

Consumers use these contracts to depend on HTTP abstractions without
importing the full lexigram-http implementation.
"""

from __future__ import annotations

from lexigram.contracts.web.http_protocols import (
    HTTPClientProtocol as HTTPClientProtocol,
)
from lexigram.contracts.web.http_protocols import (
    InterceptorChainProtocol as InterceptorChainProtocol,
)
from lexigram.contracts.web.http_protocols import (
    InterceptorProtocol as InterceptorProtocol,
)

__all__ = [
    "HTTPClientProtocol",
    "InterceptorChainProtocol",
    "InterceptorProtocol",
]
