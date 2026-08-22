"""End-to-end tests over the JSON API."""

from __future__ import annotations

import httpx


async def test_templates_listed(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/templates")).json()

    assert {t["variant"] for t in body} == {"v1", "v2"}
    assert all({"variant", "label", "active_rev"} <= set(t) for t in body)


async def test_render_current(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/render",
        json={
            "variant": "v1",
            "vars": {"issue": "late parcel", "tone": "neutral"},
        },
    )

    assert response.status_code == 200
    assert "late parcel" in response.json()["rendered"]


async def test_render_specific_revision(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/render",
        json={
            "variant": "v2",
            "rev": 2,
            "vars": {"issue": "late parcel", "tone": "warm"},
        },
    )

    assert response.status_code == 200
    rendered = response.json()["rendered"]
    assert "happy to help" in rendered  # same template body at any revision


async def test_render_unknown_variable_is_400(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/render",
        json={"variant": "v1", "vars": {"bogus": "x"}},
    )

    assert response.status_code == 400
    assert "missing" in response.json()["error"].lower()


async def test_history_and_rollback(client: httpx.AsyncClient) -> None:
    history = (await client.get("/api/history/v2")).json()["entries"]
    assert len(history) == 2

    rolled = await client.post("/api/rollback", json={"variant": "v2"})
    assert rolled.json()["active_rev"] == 1

    after = (await client.get("/api/history/v2")).json()["entries"]
    assert len(after) == 2  # history preserved; pointer moved
    assert [e["current"] for e in after] == [True, False]


async def test_ab_endpoint_stable(client: httpx.AsyncClient) -> None:
    first = (await client.post("/api/ab")).json()
    second = (await client.post("/api/ab")).json()

    assert first == second
    assert first["winner"] == "v2"


async def test_unknown_variant_is_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/history/nope")

    assert response.status_code == 404
