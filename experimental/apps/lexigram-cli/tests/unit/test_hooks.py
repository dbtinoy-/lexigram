from __future__ import annotations


class TestHooksModule:
    def test_module_exists(self) -> None:
        from lexigram.cli import hooks
        assert hooks.__doc__ is not None
