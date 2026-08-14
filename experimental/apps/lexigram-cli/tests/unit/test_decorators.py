from __future__ import annotations


class TestDecoratorsModule:
    def test_module_exists(self) -> None:
        from lexigram.cli import decorators
        assert decorators.__doc__ is not None
