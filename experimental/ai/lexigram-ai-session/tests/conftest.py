"""Shared fixtures for lexigram-ai-session unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from lexigram.contracts.ai.session import SessionState, SessionStatus, SessionTurn
from lexigram.ai.session.config import SessionConfig
from lexigram.ai.session.manager import SessionManagerImpl
from lexigram.ai.session.stores.in_memory import InMemorySessionStore


@pytest.fixture
def store() -> InMemorySessionStore:
    """Fresh in-memory session store."""
    return InMemorySessionStore()


@pytest.fixture
def config() -> SessionConfig:
    """Session config with auto-checkpoint disabled for simplicity."""
    return SessionConfig(auto_checkpoint_interval=None)


@pytest.fixture
def manager(store: InMemorySessionStore, config: SessionConfig) -> SessionManagerImpl:
    """Session manager backed by the in-memory store."""
    return SessionManagerImpl(config=config, store=store)


@pytest.fixture
def make_state():
    """Factory for creating test SessionState instances."""
    def _make(
        user_id: str = "user1",
        status: SessionStatus = SessionStatus.ACTIVE,
        session_id: str | None = None,
        turns: list[SessionTurn] | None = None,
        variables: dict | None = None,
        total_tokens: int = 0,
        total_cost: float = 0.0,
    ) -> SessionState:
        now = datetime.now(UTC)
        return SessionState(
            session_id=session_id or str(uuid4()),
            user_id=user_id,
            status=status,
            created_at=now,
            updated_at=now,
            turns=turns or [],
            variables=variables or {},
            total_tokens=total_tokens,
            total_cost=total_cost,
        )
    return _make


@pytest.fixture
def make_turn():
    """Factory for creating test SessionTurn instances."""
    def _make(
        role: str = "user",
        content: str = "hello",
        tokens_used: int = 0,
        cost: float = 0.0,
        metadata: dict | None = None,
    ) -> SessionTurn:
        return SessionTurn(
            turn_id=str(uuid4()),
            role=role,
            content=content,
            timestamp=datetime.now(UTC),
            tokens_used=tokens_used,
            cost=cost,
            metadata=metadata or {},
        )
    return _make
