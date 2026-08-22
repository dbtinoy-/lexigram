"""Tests for declarative fact extraction."""

from __future__ import annotations

from memory_chat.services.extraction import extract_facts


class TestExtractFacts:
    def test_diet_statement(self) -> None:
        triples = extract_facts("alice", "I'm vegetarian")

        assert triples == [("alice", "diet", "vegetarian", 0.9)]

    def test_allergy_statement(self) -> None:
        triples = extract_facts("alice", "I am allergic to peanuts")

        assert triples == [("alice", "allergy", "peanuts", 0.95)]

    def test_preference_statement(self) -> None:
        triples = extract_facts("bob", "I like spicy food")

        assert triples == [("bob", "preference", "spicy", 0.7)]

    def test_have_allergy_form(self) -> None:
        triples = extract_facts("bob", "I have a nut allergy")

        assert triples == [("bob", "allergy", "nut", 0.95)]

    def test_multiple_facts_deduped(self) -> None:
        triples = extract_facts("alice", "I'm vegetarian. I'm vegetarian!")

        assert len(triples) == 1

    def test_no_false_positives(self) -> None:
        assert extract_facts("bob", "The dog likes treats") == []
        assert extract_facts("bob", "Tell me a joke") == []

    def test_subject_is_owner_id(self) -> None:
        alice = extract_facts("alice", "I'm vegan")
        bob = extract_facts("bob", "I'm vegan")

        assert alice[0][0] == "alice"
        assert bob[0][0] == "bob"
