"""Service-level tests resolved from the booted container."""

from __future__ import annotations

from memory_chat.services.chat_service import ConciergeService


async def test_fact_stated_turn_one_cited_later(app) -> None:
    service = await app.container.resolve(ConciergeService)

    for text in ("I'm vegetarian", "I'm allergic to peanuts"):
        assert (await service.send("alice", text)).is_ok()
    result = await service.send("alice", "Suggest a dinner menu")

    assert result.is_ok()
    turn = result.unwrap()
    assert "peanuts" in turn.reply_text
    assert "vegetarian" in turn.reply_text
    assert turn.cited == ["diet: vegetarian", "allergy: peanuts"]
    assert turn.context_chars > 0


async def test_cross_owner_isolation_through_shared_backend(app) -> None:
    service = await app.container.resolve(ConciergeService)

    await service.send("alice", "I'm allergic to peanuts")
    bob_result = await service.send("bob", "Suggest a dinner menu")
    assert bob_result.is_ok()
    bob_menu = bob_result.unwrap()

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

    assert (await service.send("carol", "I like spicy food")).is_ok()
    snapshot = await service.get_facts("carol")

    assert snapshot.triples == [["carol", "preference", "spicy", 0.7]]
    assert [e.content for e in snapshot.recent] == ["I like spicy food"]


async def test_blank_message_is_err(app) -> None:
    from lexigram.result import Err

    service = await app.container.resolve(ConciergeService)
    result = await service.send("alice", "   ")

    assert isinstance(result, Err)
