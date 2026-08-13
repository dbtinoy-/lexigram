"""Protocol re-exports for session management — convenience surface for consumers."""

from __future__ import annotations

from lexigram.contracts.ai.session import (
    ContextPrunerProtocol as ContextPrunerProtocol,
)
from lexigram.contracts.ai.session import (
    SessionContextProtocol as SessionContextProtocol,
)
from lexigram.contracts.ai.session import (
    SessionManagerProtocol as SessionManagerProtocol,
)
from lexigram.contracts.ai.session import (
    SessionStoreProtocol as SessionStoreProtocol,
)

__all__ = [
    "ContextPrunerProtocol",
    "SessionContextProtocol",
    "SessionManagerProtocol",
    "SessionStoreProtocol",
]
