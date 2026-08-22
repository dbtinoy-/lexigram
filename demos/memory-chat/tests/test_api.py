"""End-to-end tests over the JSON API."""

from __future__ import annotations

import httpx


async def test_chat_turn_shape(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/chat",
        json={"owner": "alice", "text": "I'm vegetarian"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["cited"] == ["diet: vegetarian"]
    assert isinstance(body["context_chars"], int)


async def test_recall_across_turns(client: httpx.AsyncClient) -> None:
    await client.post(
        "/api/chat",
        json={"owner": "alice", "text": "I'm allergic to peanuts"},
    )
    menu = await client.post(
        "/api/chat",
        json={"owner": "alice", "text": "Suggest a dinner menu"},
    )

    body = menu.json()
    assert "peanuts" in body["reply"]


async def test_owner_isolation(client: httpx.AsyncClient) -> None:
    await client.post(
        "/api/chat",
        json={"owner": "alice", "text": "I'm allergic to peanuts"},
    )
    bob = await client.post(
        "/api/chat",
        json={"owner": "bob", "text": "What do you remember about me?"},
    )

    assert bob.json()["reply"] == "Noted! What would you like next?"
    facts_bob = (await client.get("/api/facts/bob")).json()
    assert facts_bob["triples"] == []


async def test_demo_endpoint_stable(client: httpx.AsyncClient) -> None:
    await client.post("/api/demo")            # warm-up stores facts
    second = (await client.post("/api/demo")).json()
    third = (await client.post("/api/demo")).json()

    assert second == third                    # stable post-warmup
    assert second["isolation_ok"] is True


async def test_empty_text_is_400(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/chat",
        json={"owner": "alice", "text": "   "},
    )

    assert response.status_code == 400
