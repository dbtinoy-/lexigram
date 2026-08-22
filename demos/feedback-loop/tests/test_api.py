"""End-to-end tests over the JSON API."""

from __future__ import annotations

import httpx


async def test_ask_returns_trace(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/ask",
        json={"key": "track-order", "owner": "web-user"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"] == "t3"
    assert "tracking id" in body["answer"]


async def test_ask_unknown_key_is_400(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/ask", json={"key": "nope"})

    assert response.status_code == 400


async def test_rate_then_stats(client: httpx.AsyncClient) -> None:
    ask = await client.post("/api/ask", json={"key": "warranty", "owner": "alice"})
    trace = ask.json()["trace_id"]

    rated = await client.post(
        "/api/rate",
        json={"trace_id": trace, "rating": 2, "owner": "alice"},
    )
    assert rated.status_code == 200

    stats = (await client.get("/api/stats/alice")).json()
    assert stats["total"] == 1
    assert stats["average"] == 2.0


async def test_rate_invalid_is_400(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/rate",
        json={"trace_id": "t9", "rating": 5, "owner": "alice"},
    )

    assert response.status_code == 400


async def test_regress_and_report(client: httpx.AsyncClient) -> None:
    for key, rating in (("refund-policy", 1), ("shipping-time", 2)):
        ask = await client.post("/api/ask", json={"key": key, "owner": "bob"})
        await client.post(
            "/api/rate",
            json={"trace_id": ask.json()["trace_id"], "rating": rating,
                  "owner": "bob"},
        )
    for key in ("track-order", "warranty"):
        ask = await client.post("/api/ask", json={"key": key, "owner": "bob"})
        await client.post(
            "/api/rate",
            json={"trace_id": ask.json()["trace_id"], "rating": 5,
                  "owner": "bob"},
        )

    regressed = await client.post("/api/regress", json={"owner": "bob"})
    assert regressed.status_code == 200
    summary = regressed.json()
    assert set(summary["failing_ids"]) == {"t1", "t2"}

    report = (await client.get(f"/api/report/{summary['run_id']}")).json()
    assert report["error_count"] == 0
    assert report["total_records"] >= 2


async def test_regress_without_low_ratings_is_400(
    client: httpx.AsyncClient,
) -> None:
    await client.post("/api/ask", json={"key": "track-order", "owner": "carol"})
    await client.post(
        "/api/rate", json={"trace_id": "t3", "rating": 5, "owner": "carol"},
    )

    response = await client.post("/api/regress", json={"owner": "carol"})

    assert response.status_code == 400
