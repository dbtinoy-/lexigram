"""P3 hook surface import verification for lexigram-ai-session."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest


def test_session_hooks_root_module_exists() -> None:
    import lexigram.ai.session
    from lexigram.ai.session.hooks import (
        SessionCheckpointCreatedHook,
        SessionClosedHook,
        SessionStartedHook,
    )

    assert lexigram.ai.session.SessionStartedHook is SessionStartedHook
    assert (
        lexigram.ai.session.SessionCheckpointCreatedHook
        is SessionCheckpointCreatedHook
    )
    assert lexigram.ai.session.SessionClosedHook is SessionClosedHook


def test_session_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.ai.session.hooks import (
        SessionCheckpointCreatedHook,
        SessionClosedHook,
        SessionStartedHook,
    )

    started = SessionStartedHook(session_id="s1")
    checkpoint_created = SessionCheckpointCreatedHook(session_id="s1")
    closed = SessionClosedHook(session_id="s1")

    assert is_dataclass(started)
    assert is_dataclass(checkpoint_created)
    assert is_dataclass(closed)
    assert [field.name for field in fields(started)] == ["session_id"]
    assert [field.name for field in fields(checkpoint_created)] == ["session_id"]
    assert [field.name for field in fields(closed)] == ["session_id"]

    with pytest.raises(TypeError):
        SessionStartedHook("s1")  # type: ignore[misc]

    with pytest.raises(TypeError):
        SessionCheckpointCreatedHook("s1")  # type: ignore[misc]

    with pytest.raises(TypeError):
        SessionClosedHook("s1")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        started.session_id = "s2"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        checkpoint_created.session_id = "s2"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        closed.session_id = "s2"  # type: ignore[misc]
