from __future__ import annotations

from lexigram.nosql import decorators


class TestDecoratorsModule:
    def test_module_exists(self) -> None:
        assert hasattr(decorators, "__doc__")
