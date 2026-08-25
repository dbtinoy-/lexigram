"""Health endpoint test through the full fake-backed HTTP stack."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.http._harness import build_sync_client


@pytest.fixture()
def harness(tmp_path: Path):
    h = build_sync_client(tmp_path)
    yield h
    loop = getattr(h.client, "_builder_loop", None)
    if loop is not None:
        loop.close()


def test_health_endpoint_returns_ok(harness) -> None:
    from lexigram.builder.constants import __version__

    response = harness.client.get("/builder/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
