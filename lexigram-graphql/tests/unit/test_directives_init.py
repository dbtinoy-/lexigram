from __future__ import annotations

from lexigram.graphql.directives import DeprecationDirectiveHandler, DirectiveRegistry


class TestDirectivesInit:
    def test_exports_deprecation_handler(self) -> None:
        assert DeprecationDirectiveHandler is not None

    def test_exports_directive_registry(self) -> None:
        assert DirectiveRegistry is not None
