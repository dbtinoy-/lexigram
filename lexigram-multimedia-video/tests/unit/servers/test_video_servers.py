"""Tests for the video reference servers' explicit body caps (security D4)."""

from __future__ import annotations


def test_svd_server_caps_body_size() -> None:
    from lexigram.multimedia.video.servers.svd_server import MAX_BODY_BYTES

    assert isinstance(MAX_BODY_BYTES, int) and MAX_BODY_BYTES >= 64 * 1024 * 1024


def test_cogvideox_server_caps_body_size() -> None:
    from lexigram.multimedia.video.servers.cogvideox_server import MAX_BODY_BYTES

    assert isinstance(MAX_BODY_BYTES, int) and MAX_BODY_BYTES >= 64 * 1024 * 1024


def test_wan22_server_caps_body_size() -> None:
    from lexigram.multimedia.video.servers.wan22_server import MAX_BODY_BYTES

    assert isinstance(MAX_BODY_BYTES, int) and MAX_BODY_BYTES >= 64 * 1024 * 1024