from __future__ import annotations

from lexigram.graphql.directives.builtin import DeprecationDirectiveHandler


class _AttribTarget:
    pass


class TestDeprecationDirectiveHandler:
    def test_apply_deprecated_sets_reason(self) -> None:
        handler = DeprecationDirectiveHandler()
        target = _AttribTarget()
        result = handler.apply_directive("deprecated", {"reason": "Use new API"}, target)
        assert result is target
        assert result.__deprecated__ == "Use new API"

    def test_apply_deprecated_default_reason(self) -> None:
        handler = DeprecationDirectiveHandler()
        target = _AttribTarget()
        result = handler.apply_directive("deprecated", {}, target)
        assert result.__deprecated__ == "No longer supported."

    def test_apply_deprecated_non_attrib_target(self) -> None:
        handler = DeprecationDirectiveHandler()
        target = None
        result = handler.apply_directive("deprecated", {"reason": "x"}, target)
        assert result is target
