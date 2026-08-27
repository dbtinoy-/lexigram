"""End-to-end tests over the JSON API.

These tests hit the full stack — real DI, real services,
real HTTP routing.  They validate that the composition root wires
everything correctly and that the API contract matches expectations.
For unit tests, mock GuardPipelineProtocol in isolation.
"""

from __future__ import annotations

import httpx

ACT_ORDER = ["injection", "pii", "length", "model"]


async def test_ask_by_act_key(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/ask", json={"act": "pii"})

    assert response.status_code == 200
    body = response.json()["outcome"]
    assert body["kind"] == "redacted"
    assert "[REDACTED:EMAIL]" in body["reply"]


async def test_unknown_act_is_404(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/ask", json={"act": "nope"})

    assert response.status_code == 404
    assert "unknown act" in response.json()["detail"]


async def test_ask_raw_text(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/ask",
        json={"text": "Tell me about warranty.", "model": "gpt-4o-mini"},
    )

    assert response.status_code == 200
    assert response.json()["outcome"]["kind"] == "pass"


async def test_policy_toggle_endpoint(client: httpx.AsyncClient) -> None:
    off = await client.post("/api/policy", json={"enabled": False})
    assert off.json()["enabled"] is False

    bypassed = await client.post("/api/ask", json={"act": "injection"})
    assert bypassed.json()["outcome"]["kind"] == "pass"

    on = await client.post("/api/policy", json={"enabled": True})
    assert on.json()["enabled"] is True


async def test_state_reflects_spend(client: httpx.AsyncClient) -> None:
    await client.post("/api/ask", json={"act": "pii"})
    state = (await client.get("/api/state")).json()

    assert state["policy_enabled"] is True
    assert abs(state["spent"] - 0.15) < 1e-9
    assert abs(state["remaining"] - 0.35) < 1e-9


async def test_audit_rows_after_denial(client: httpx.AsyncClient) -> None:
    import asyncio

    for key in ACT_ORDER:
        await client.post("/api/ask", json={"act": key})

    # governance emits audit events fire-and-forget; yield once so the
    # scheduled record() tasks complete before querying
    await asyncio.sleep(0)

    rows = (await client.get("/api/audit")).json()["rows"]
    kinds = {r["event_type"] for r in rows}

    assert "model_denied" in kinds
