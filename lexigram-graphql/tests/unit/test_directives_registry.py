from __future__ import annotations

from typing import Any

from lexigram.graphql.directives.registry import DirectiveRegistry


class TestDirectiveRegistry:
    def test_register_and_apply(self) -> None:
        registry = DirectiveRegistry()
        target: dict[str, Any] = {}

        registry.register("upper", lambda _name, _args, t: t.upper())  # type: ignore[arg-type]
        result = registry.apply_directive("upper", {}, "hello")
        assert result == "HELLO"

    def test_on_decorator(self) -> None:
        registry = DirectiveRegistry()

        @registry.on("lower")
        def lower(_name: str, _args: dict[str, Any], target: str) -> str:
            return target.lower()

        result = registry.apply_directive("lower", {}, "HELLO")
        assert result == "hello"

    def test_unknown_directive_returns_target(self) -> None:
        registry = DirectiveRegistry()
        result = registry.apply_directive("unknown", {}, "target")
        assert result == "target"

    def test_default_handler(self) -> None:
        def default(name: str, _args: dict[str, Any], target: Any) -> str:
            return f"{name}:{target}"

        registry = DirectiveRegistry(default_handler=default)
        result = registry.apply_directive("foo", {}, "bar")
        assert result == "foo:bar"

    def test_contains(self) -> None:
        registry = DirectiveRegistry()
        assert "foo" not in registry
        registry.register("foo", lambda *a: None)
        assert "foo" in registry

    def test_repr(self) -> None:
        registry = DirectiveRegistry()
        registry.register("a", lambda *a: None)
        registry.register("b", lambda *a: None)
        r = repr(registry)
        assert r == "DirectiveRegistry(directives=['a', 'b'])"
