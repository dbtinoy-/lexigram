"""Service-level tests resolved from the booted container."""

from __future__ import annotations

from memory_chat.chat_service import ConciergeService


async def test_fact_stated_turn_one_cited_later(app) -> None:
    service = await app.container.resolve(ConciergeService)

    await service.send("alice", "I'm vegetarian")
    await service.send("alice", "I'm allergic to peanuts")
    result = await service.send("alice", "Suggest a dinner menu")

    assert "peanuts" in result.reply_text
    assert "vegetarian" in result.reply_text
    assert result.cited == ["diet: vegetarian", "allergy: peanuts"]
    assert result.context_chars > 0


async def test_cross_owner_isolation_through_shared_backend(app) -> None:
    service = await app.container.resolve(ConciergeService)

    await service.send("alice", "I'm allergic to peanuts")
    bob_menu = await service.send("bob", "Suggest a dinner menu")

    assert bob_menu.reply_text == "Here's a menu idea — anything goes!"
    snapshot = await service.get_facts("bob")
    assert snapshot.triples == []


async def test_demo_replay_is_byte_stable_and_proves_isolation(app) -> None:
    service = await app.container.resolve(ConciergeService)

    await service.demo_replay()   # warm-up: facts accumulate in-process
    second = await service.demo_replay()
    third = await service.demo_replay()

    # Fresh-boot replays are byte-identical; inside one process the first
    # run stores facts, so stability holds from the second replay onward.
    assert second.isolation_ok is True
    assert second.transcript == third.transcript
    assert third.isolation_ok is True
    assert second.transcript[2]["reply"] == (
        "Here's a menu idea — strictly avoiding peanuts "
        "while keeping things vegetarian."
    )


async def test_get_facts_snapshot_shape(app) -> None:
    service = await app.container.resolve(ConciergeService)

    await service.send("carol", "I like spicy food")
    snapshot = await service.get_facts("carol")

    assert snapshot.triples == [["carol", "preference", "spicy", 0.7]]
    assert [e.content for e in snapshot.recent] == ["I like spicy food"]
