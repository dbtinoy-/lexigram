"""Exceptions for the resilient rates demo.

Convention followed: **Exception hierarchy** — base domain exceptions live
in ``lexigram-contracts``, leaf exceptions live in the demo package.
The hierarchy is:

```
InfrastructureError (lexigram-contracts)
  └── RateProviderError
        ├── UpstreamTimeoutError
        ├── UpstreamUnavailableError
        └── RateUnavailableError
```

``RateUnavailableError`` is mapped to HTTP 503 via
``ResultResponseMapper.register()`` in the API controller — the only place
that knows the HTTP semantics.
"""

from __future__ import annotations

from lexigram.contracts.exceptions import InfrastructureError


class RateProviderError(InfrastructureError):
    """Base error for simulated rate-provider failures."""


class UpstreamTimeoutError(RateProviderError):
    """Raised when the simulated upstream is too slow to answer."""


class UpstreamUnavailableError(RateProviderError):
    """Raised when the simulated upstream is hard-down."""


class RateUnavailableError(RateProviderError):
    """Raised when no quote is obtainable and no stale copy exists."""


__all__ = [
    "RateProviderError",
    "RateUnavailableError",
    "UpstreamTimeoutError",
    "UpstreamUnavailableError",
]
