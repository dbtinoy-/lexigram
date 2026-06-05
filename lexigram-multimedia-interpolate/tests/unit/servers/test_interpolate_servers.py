"""Tests for the interpolate reference server's explicit body cap (security D4)."""

from __future__ import annotations


def test_rife_server_caps_body_size() -> None:
    from lexigram.multimedia.interpolate.servers.rife_server import MAX_BODY_BYTES

    assert isinstance(MAX_BODY_BYTES, int) and MAX_BODY_BYTES >= 64 * 1024 * 1024