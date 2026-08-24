"""Tests for lexigram.ai.types."""

from __future__ import annotations


class TestAIBaseEvent:
    """Tests for lexigram.ai.types.AIBaseEvent."""

    def test_ai_base_event_has_timestamp(self) -> None:
        from datetime import datetime
        from lexigram.ai.types import AIBaseEvent

        event = AIBaseEvent()
        assert isinstance(event.timestamp, datetime)

    def test_ai_base_event_has_metadata(self) -> None:
        from lexigram.ai.types import AIBaseEvent

        event = AIBaseEvent()
        assert isinstance(event.metadata, dict)
        assert event.metadata == {}

    def test_ai_base_event_accepts_metadata(self) -> None:
        from lexigram.ai.types import AIBaseEvent

        event = AIBaseEvent(metadata={"source": "test", "version": 1})
        assert event.metadata["source"] == "test"
        assert event.metadata["version"] == 1

    def test_ai_types_all_exports(self) -> None:
        import lexigram.ai.types as types_mod

        for name in types_mod.__all__:
            assert hasattr(types_mod, name), f"Missing export: {name}"
