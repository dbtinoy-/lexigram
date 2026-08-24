"""HTTP web protocol definitions.

Structural protocols for the HTTP request/response lifecycle, middleware,
rate limiting, exception filtering, and web provider integration.
"""

from __future__ import annotations

from lexigram.contracts.core.middleware import (
    ExceptionFilterChainProtocol as ExceptionFilterChainProtocol,
)
from lexigram.contracts.web.protocols.app import (
    BackgroundTaskRunnerProtocol as BackgroundTaskRunnerProtocol,
)
from lexigram.contracts.web.protocols.app import (
    ConnectionManagerProtocol as ConnectionManagerProtocol,
)
from lexigram.contracts.web.protocols.app import (
    CRUDServiceProtocol as CRUDServiceProtocol,
)
from lexigram.contracts.web.protocols.app import (
    CSRFProtectionProtocol as CSRFProtectionProtocol,
)
from lexigram.contracts.web.protocols.app import (
    HTTPApplicationProtocol as HTTPApplicationProtocol,
)
from lexigram.contracts.web.protocols.app import (
    WebContributorProtocol as WebContributorProtocol,
)
from lexigram.contracts.web.protocols.app import (
    WebProviderProtocol as WebProviderProtocol,
)
from lexigram.contracts.web.protocols.http import (
    CORSPolicyProtocol as CORSPolicyProtocol,
)
from lexigram.contracts.web.protocols.http import (
    HttpRequestLoggerProtocol as HttpRequestLoggerProtocol,
)
from lexigram.contracts.web.protocols.http import RequestProtocol as RequestProtocol
from lexigram.contracts.web.protocols.http import (
    ResponseFactoryProtocol as ResponseFactoryProtocol,
)
from lexigram.contracts.web.protocols.http import ResponseProtocol as ResponseProtocol
from lexigram.contracts.web.protocols.http import (
    WebRateLimiterProtocol as WebRateLimiterProtocol,
)
from lexigram.contracts.web.protocols.middleware import (
    ExceptionFilterProtocol as ExceptionFilterProtocol,
)
from lexigram.contracts.web.protocols.middleware import (
    WebMiddlewareProtocol as WebMiddlewareProtocol,
)

__all__ = [
    "BackgroundTaskRunnerProtocol",
    "CORSPolicyProtocol",
    "CRUDServiceProtocol",
    "CSRFProtectionProtocol",
    "ConnectionManagerProtocol",
    "ExceptionFilterChainProtocol",
    "ExceptionFilterProtocol",
    "HTTPApplicationProtocol",
    "HttpRequestLoggerProtocol",
    "RequestProtocol",
    "ResponseFactoryProtocol",
    "ResponseProtocol",
    "WebContributorProtocol",
    "WebMiddlewareProtocol",
    "WebProviderProtocol",
    "WebRateLimiterProtocol",
]
