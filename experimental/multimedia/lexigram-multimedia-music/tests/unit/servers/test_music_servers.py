"""Tests for the music reference servers' explicit body caps (security D4)."""

from __future__ import annotations


def test_ace_step_server_caps_body_size() -> None:
    from lexigram.multimedia.music.servers.ace_step_server import MAX_BODY_BYTES

    assert isinstance(MAX_BODY_BYTES, int) and MAX_BODY_BYTES >= 64 * 1024 * 1024


def test_stable_audio_open_server_caps_body_size() -> None:
    from lexigram.multimedia.music.servers.stable_audio_open_server import (
        MAX_BODY_BYTES,
    )

    assert isinstance(MAX_BODY_BYTES, int) and MAX_BODY_BYTES >= 64 * 1024 * 1024
