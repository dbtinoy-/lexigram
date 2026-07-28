"""lexigram-ai-session — stateful conversation session management.

Provides tools for managing conversation history, branching,
checkpointing, and multi-agent group sessions.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

try:
    __version__ = version("lexigram-ai-session")
except PackageNotFoundError:
    __version__ = "0.0.0"

if TYPE_CHECKING:
    from lexigram.ai.session.analytics.core import SessionAnalytics
    from lexigram.ai.session.branching.branch_manager import BranchManager
    from lexigram.ai.session.branching.merge import (
        AppendMerge,
        MergeStrategy,
        SelectiveMerge,
    )
    from lexigram.ai.session.checkpointing.checkpoint_manager import CheckpointManager
    from lexigram.ai.session.checkpointing.diff import StateDiff
    from lexigram.ai.session.config import SessionConfig
    from lexigram.ai.session.context import RelevanceContextPruner, SessionContext
    from lexigram.ai.session.di.provider import SessionProvider
    from lexigram.ai.session.exceptions import (
        CheckpointNotFoundError,
        SessionCapacityError,
        SessionClosedError,
        SessionError,
        SessionExpiredError,
        SessionNotFoundError,
        SessionTransitionError,
    )
    from lexigram.ai.session.hooks import (
        SessionCheckpointCreatedHook,
        SessionClosedHook,
        SessionStartedHook,
    )
    from lexigram.ai.session.manager import SessionManagerImpl
    from lexigram.ai.session.middleware.session_middleware import SessionMiddleware
    from lexigram.ai.session.module import SessionModule
    from lexigram.ai.session.multi_agent.group_session import GroupSession
    from lexigram.ai.session.multi_agent.role_isolation import RoleIsolation
    from lexigram.ai.session.multi_agent.turn_manager import (
        PriorityTurnManager,
        RoundRobinTurnManager,
        TopicBasedTurnManager,
        TurnManager,
    )
    from lexigram.ai.session.state import SessionStateMachine
    from lexigram.ai.session.stores.cache import CacheSessionStore
    from lexigram.ai.session.stores.database import DatabaseSessionStore
    from lexigram.ai.session.stores.in_memory import InMemorySessionStore
    from lexigram.ai.session.types import Metadata, SessionId, TurnId

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # --- Branching ---
    "BranchManager": ("lexigram.ai.session.branching.branch_manager", "BranchManager"),
    "AppendMerge": ("lexigram.ai.session.branching.merge", "AppendMerge"),
    "MergeStrategy": ("lexigram.ai.session.branching.merge", "MergeStrategy"),
    "SelectiveMerge": ("lexigram.ai.session.branching.merge", "SelectiveMerge"),
    # --- Checkpointing ---
    "CheckpointManager": (
        "lexigram.ai.session.checkpointing.checkpoint_manager",
        "CheckpointManager",
    ),
    "StateDiff": ("lexigram.ai.session.checkpointing.diff", "StateDiff"),
    # --- Config ---
    "SessionConfig": ("lexigram.ai.session.config", "SessionConfig"),
    # --- Context ---
    "SessionContext": ("lexigram.ai.session.context", "SessionContext"),
    "RelevanceContextPruner": ("lexigram.ai.session.context", "RelevanceContextPruner"),
    # --- DI ---
    "SessionProvider": ("lexigram.ai.session.di.provider", "SessionProvider"),
    # --- Analytics ---
    "SessionAnalytics": ("lexigram.ai.session.analytics.core", "SessionAnalytics"),
    # --- Exceptions ---
    "CheckpointNotFoundError": (
        "lexigram.ai.session.exceptions",
        "CheckpointNotFoundError",
    ),
    "SessionCapacityError": ("lexigram.ai.session.exceptions", "SessionCapacityError"),
    "SessionClosedError": ("lexigram.ai.session.exceptions", "SessionClosedError"),
    "SessionError": ("lexigram.ai.session.exceptions", "SessionError"),
    "SessionExpiredError": ("lexigram.ai.session.exceptions", "SessionExpiredError"),
    "SessionNotFoundError": ("lexigram.ai.session.exceptions", "SessionNotFoundError"),
    "SessionTransitionError": (
        "lexigram.ai.session.exceptions",
        "SessionTransitionError",
    ),
    # --- Hooks ---
    "SessionCheckpointCreatedHook": (
        "lexigram.ai.session.hooks",
        "SessionCheckpointCreatedHook",
    ),
    "SessionClosedHook": ("lexigram.ai.session.hooks", "SessionClosedHook"),
    "SessionStartedHook": ("lexigram.ai.session.hooks", "SessionStartedHook"),
    # --- Manager ---
    "SessionManager": ("lexigram.ai.session.manager", "SessionManagerImpl"),
    "SessionManagerImpl": ("lexigram.ai.session.manager", "SessionManagerImpl"),
    # --- Middleware ---
    "SessionMiddleware": (
        "lexigram.ai.session.middleware.session_middleware",
        "SessionMiddleware",
    ),
    # --- Module ---
    "SessionModule": ("lexigram.ai.session.module", "SessionModule"),
    # --- Multi-Agent ---
    "GroupSession": ("lexigram.ai.session.multi_agent.group_session", "GroupSession"),
    "RoleIsolation": (
        "lexigram.ai.session.multi_agent.role_isolation",
        "RoleIsolation",
    ),
    "PriorityTurnManager": (
        "lexigram.ai.session.multi_agent.turn_manager",
        "PriorityTurnManager",
    ),
    "RoundRobinTurnManager": (
        "lexigram.ai.session.multi_agent.turn_manager",
        "RoundRobinTurnManager",
    ),
    "TopicBasedTurnManager": (
        "lexigram.ai.session.multi_agent.turn_manager",
        "TopicBasedTurnManager",
    ),
    "TurnManager": ("lexigram.ai.session.multi_agent.turn_manager", "TurnManager"),
    # --- State ---
    "SessionStateMachine": ("lexigram.ai.session.state", "SessionStateMachine"),
    # --- Stores ---
    "CacheSessionStore": ("lexigram.ai.session.stores.cache", "CacheSessionStore"),
    "DatabaseSessionStore": (
        "lexigram.ai.session.stores.database",
        "DatabaseSessionStore",
    ),
    "InMemorySessionStore": (
        "lexigram.ai.session.stores.in_memory",
        "InMemorySessionStore",
    ),
    # --- Types ---
    "Metadata": ("lexigram.ai.session.types", "Metadata"),
    "SessionId": ("lexigram.ai.session.types", "SessionId"),
    "TurnId": ("lexigram.ai.session.types", "TurnId"),
    # --- Events ---
    "SessionCreatedEvent": ("lexigram.ai.session.events", "SessionCreatedEvent"),
    "SessionClosedEvent": ("lexigram.ai.session.events", "SessionClosedEvent"),
    # --- Protocols ---
    "ContextPrunerProtocol": ("lexigram.ai.session.protocols", "ContextPrunerProtocol"),
    "SessionContextProtocol": (
        "lexigram.ai.session.protocols",
        "SessionContextProtocol",
    ),
    "SessionManagerProtocol": (
        "lexigram.ai.session.protocols",
        "SessionManagerProtocol",
    ),
    "SessionStoreProtocol": ("lexigram.ai.session.protocols", "SessionStoreProtocol"),
}


def __getattr__(name: str) -> Any:
    """Lazy-load symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Enumerate available attributes for IDE support."""
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS)
