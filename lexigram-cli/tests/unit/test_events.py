from __future__ import annotations


class TestEventsModule:
    def test_module_exists(self) -> None:
        from lexigram.cli import events
        assert events.__doc__ is not None
