"""Re-exports for the security subsystem.

Re-exports ``GuardError`` from contracts.  The ``GuardProtocol``
is imported from ``lexigram.contracts.web.guard``.
"""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import (
    GuardError as GuardError,  # re-export
)

__all__ = [
    "GuardError",
]
