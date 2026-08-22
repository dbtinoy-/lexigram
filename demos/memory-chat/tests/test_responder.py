"""Tests for the deterministic template responder."""

from __future__ import annotations

from memory_chat.responder import reply_for


ALICE_FACTS = [
    ("alice", "diet", "vegetarian", 0.9),
    ("alice", "allergy", "peanuts", 0.95),
]
BOB_FACTS: list = []


class TestReplyFor:
    def test_food_intent_with_constraints_cites_them(self) -> None:
        reply = reply_for("Suggest a dinner menu", ALICE_FACTS)

        assert "peanuts" in reply.text
        assert "vegetarian" in reply.text
        assert reply.cited == ["diet: vegetarian", "allergy: peanuts"]

    def test_food_intent_without_constraints_anything_goes(self) -> None:
        reply = reply_for("Suggest a dinner menu", BOB_FACTS)

        assert reply.text == "Here's a menu idea — anything goes!"
        assert reply.cited == []

    def test_remember_intent_lists_facts(self) -> None:
        reply = reply_for("What do you remember about me?", ALICE_FACTS)

        assert "diet: vegetarian" in reply.text
        assert reply.cited == ["diet: vegetarian", "allergy: peanuts"]

    def test_plain_turn_acknowledges(self) -> None:
        reply = reply_for("hello there", [])

        assert reply.text == "Noted! What would you like next?"
        assert reply.cited == []
