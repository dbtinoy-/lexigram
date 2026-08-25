"""HTTP API tests: CRUD, validation diagnostics, generation kick, SSE, proxy."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from lexigram.builder.graph.models import (
    AppSettingsConfig,
    EntityConfig,
    FieldConfig,
    GraphDocument,
    GraphNode,
    Position,
)
from tests.unit.http._harness import build_sync_client


VALID_GRAPH = {
    "version": 1,
    "nodes": [
        {
            "id": "app_1",
            "kind": "app_settings",
            "position": {"x": 0, "y": 0},
            "config": {"app_name": "notes_api", "port": 8000, "db": "sqlite"},
        },
        {
            "id": "ent_user",
            "kind": "entity",
            "position": {"x": 10, "y": 10},
            "config": {
                "name": "user",
                "fields": [{"name": "email", "type": "str", "nullable": False}],
            },
        },
    ],
    "edges": [],
}


@pytest.fixture()
def harness(tmp_path: Path):
    h = build_sync_client(tmp_path)
    yield h
    loop = getattr(h.client, "_builder_loop", None)
    if loop is not None:
        loop.close()


def test_health_and_palette(harness) -> None:
    r = harness.client.get("/builder/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"

    p = harness.client.get("/builder/palette")
    assert p.status_code == 200
    body = p.json()
    assert body["kinds"] == ["app_settings", "entity", "route"]
    assert {"str", "int", "float", "bool", "datetime", "uuid"} <= set(
        body["field_types"]
    )
    assert body["edges"] == [{"src": "route", "dst": "entity"}]


def test_project_crud_flow(harness) -> None:
    created = harness.client.post("/builder/projects", json={"name": "notes_api"})
    assert created.status_code == 201

    listing = harness.client.get("/builder/projects")
    assert [item["name"] for item in listing.json()] == ["notes_api"]

    dup = harness.client.post("/builder/projects", json={"name": "notes_api"})
    assert dup.status_code == 422

    bad = harness.client.post("/builder/projects", json={"name": "Bad!"})
    assert bad.status_code == 422


def test_put_get_graph_roundtrip(harness) -> None:
    harness.client.post("/builder/projects", json={"name": "notes_api"})

    put = harness.client.put("/builder/projects/notes_api/graph", json=VALID_GRAPH)
    assert put.status_code == 200

    got = harness.client.get("/builder/projects/notes_api/graph")
    assert got.status_code == 200
    assert got.json() == VALID_GRAPH

    listing = harness.client.get("/builder/projects")
    assert listing.json()[0]["preview"] is None


def test_put_invalid_graph_returns_422_with_diagnostics(harness) -> None:
    harness.client.post("/builder/projects", json={"name": "notes_api"})

    broken = {
        "version": 1,
        "nodes": [
            VALID_GRAPH["nodes"][0],
            {
                "id": "ent_bad",
                "kind": "entity",
                "position": {"x": 1, "y": 1},
                "config": {"name": "Bad!", "fields": []},
            },
        ],
        "edges": [],
    }
    put = harness.client.put("/builder/projects/notes_api/graph", json=broken)

    assert put.status_code == 422
    body = put.json()
    codes = {d["code"] for d in body["diagnostics"]}
    assert {"invalid-entity-name", "no-fields"} <= codes


def test_delete_unknown_is_404(harness) -> None:
    r = harness.client.delete("/builder/projects/ghost")
    assert r.status_code == 404


def test_generate_unknown_project_404(harness) -> None:
    r = harness.client.post("/builder/projects/ghost/generate")
    assert r.status_code == 404


def test_stop_preview_endpoint_idempotent(harness) -> None:
    harness.client.post("/builder/projects", json={"name": "alpha"})
    r = harness.client.post("/builder/projects/alpha/preview/stop")
    assert r.status_code == 200
    assert r.json() == {"stopped": True}


def test_proxy_without_live_preview_is_404(harness) -> None:
    harness.client.post("/builder/projects", json={"name": "alpha"})
    r = harness.client.post(
        "/builder/projects/alpha/preview/request?path=/users"
    )
    assert r.status_code == 404


async def test_sse_stream_delivers_published_events(tmp_path: Path) -> None:
    """Drive raw ASGI: httpx ASGITransport buffers bodies, killing live streams."""
    from tests.unit.http._harness import build_async_stack

    client, previews = await build_async_stack(tmp_path)
    try:
        transport = client._transport
        asgi_app = transport.app
        disconnect = asyncio.Event()

        async def receive() -> dict:
            await disconnect.wait()
            return {"type": "http.disconnect"}

        frames: list[str] = []
        start_status: int | None = None

        async def send(message: dict) -> None:
            nonlocal start_status
            if message["type"] == "http.response.start":
                start_status = message["status"]
            elif message["type"] == "http.response.body":
                frames.append(bytes(message.get("body", b"")).decode())
                if '"writing"' in frames[-1]:
                    disconnect.set()

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/builder/projects/x/preview/stream",
            "raw_path": b"/builder/projects/x/preview/stream",
            "query_string": b"",
            "root_path": "",
            "headers": [],
            "client": ("127.0.0.1", 1),
            "server": ("127.0.0.1", 80),
        }

        async def late_publish() -> None:
            await asyncio.sleep(0.05)
            previews.publish({"type": "phase", "phase": "writing"})

        publisher = asyncio.create_task(late_publish())

        async def run_app() -> None:
            await asgi_app(scope, receive, send)

        await asyncio.wait_for(asyncio.shield(run_app()), timeout=10)
        publisher.cancel()
        assert start_status == 200
        joined = "".join(frames)
        assert 'event: phase' in joined
        assert '"writing"' in joined
    finally:
        await client.aclose()


async def test_generate_pipeline_reaches_live(tmp_path: Path) -> None:
    from tests.unit.http._harness import build_async_stack

    client, previews = await build_async_stack(tmp_path)
    try:
        created = await client.post(
            "/builder/projects", json={"name": "notes_api"}
        )
        assert created.status_code == 201
        put = await client.put(
            "/builder/projects/notes_api/graph", json=VALID_GRAPH
        )
        assert put.status_code == 200

        queue = previews.subscribe()
        kicked = await client.post("/builder/projects/notes_api/generate")
        assert kicked.status_code == 202

        phases: list[str] = []
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=5)
            if event.get("project") == "notes_api":
                phases.append(event["phase"])
            if event.get("phase") == "live":
                break
        assert phases[:4] == ["writing", "syncing", "testing", "booting"]

        listing = (await client.get("/builder/projects")).json()
        target = next(i for i in listing if i["name"] == "notes_api")
        assert target["preview"] is not None and target["preview"]["port"] > 0
    finally:
        await client.aclose()


def _unused_nodes_guard():  # pragma: no cover - keeps imports referenced
    return GraphNode, AppSettingsConfig, EntityConfig, FieldConfig
