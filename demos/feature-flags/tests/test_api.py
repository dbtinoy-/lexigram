"""Exercise the real feature-flags composition root through HTTP."""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.asyncio
async def test_snapshot_exposes_package_evaluations(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/flags", params={"user_id": "demo-user-42", "plan": "pro"})
    assert response.status_code == 200
    data = response.json()
    assert data["cache_ttl_seconds"] == 15
    assert {flag["name"] for flag in data["flags"]} == {"new_checkout", "search_experiment", "ai_assistant"}
    assert any(flag["reason"] == "percentage_rollout" for flag in data["flags"])
    assert any(flag["variant"] for flag in data["flags"])


@pytest.mark.asyncio
async def test_attribute_context_is_visible(client: httpx.AsyncClient) -> None:
    pro = await client.get("/api/flags", params={"user_id": "u-1", "plan": "pro"})
    free = await client.get("/api/flags", params={"user_id": "u-1", "plan": "free"})
    pro_flags = {item["name"]: item for item in pro.json()["flags"]}
    free_flags = {item["name"]: item for item in free.json()["flags"]}
    assert pro_flags["ai_assistant"]["enabled"] is True
    assert free_flags["ai_assistant"]["enabled"] is False


@pytest.mark.asyncio
async def test_override_and_audit(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/flags/override", json={"name": "new_checkout", "enabled": False, "actor": "qa"})
    assert response.status_code == 200
    flags = await client.get("/api/flags", params={"user_id": "any-user"})
    item = next(flag for flag in flags.json()["flags"] if flag["name"] == "new_checkout")
    assert item["enabled"] is False
    assert item["override"] is False
    audit = await client.get("/api/flags/audit")
    assert audit.json()["count"] == 1
    assert audit.json()["entries"][0]["actor"] == "qa"


@pytest.mark.asyncio
async def test_clear_override_and_cache(client: httpx.AsyncClient) -> None:
    await client.post("/api/flags/override", json={"name": "ai_assistant", "enabled": False})
    clear = await client.post("/api/flags/override/clear", json={"name": "ai_assistant"})
    assert clear.json()["ok"] is True
    cache = await client.post("/api/flags/cache/clear")
    assert cache.json()["ok"] is True
