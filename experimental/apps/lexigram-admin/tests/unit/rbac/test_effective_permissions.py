"""Effective-permission resolver tests (R40, doc 36)."""

from __future__ import annotations

from lexigram.admin.rbac import (
    EffectivePermissions,
    resolve_effective_permissions,
)
from lexigram.contracts.auth import RoleDefinition


def _role(name: str, perms: list[str] | None = None, inherits: list[str] | None = None):
    return RoleDefinition(
        name=name,
        description="",
        permissions=perms or [],
        inherits=inherits or [],
        is_system=False,
    )


def _index(*roles) -> dict:
    return {r.name: r for r in roles}


class TestLinearChains:
    def test_no_inheritance(self) -> None:
        roles = _index(_role("viewer", ["posts.read"]))
        eff = resolve_effective_permissions("viewer", roles)
        assert eff.direct == {"posts.read"}
        assert eff.inherited == {}
        assert eff.ancestors == ()
        assert eff.missing == ()
        assert eff.all_permissions == {"posts.read"}

    def test_single_parent(self) -> None:
        roles = _index(
            _role("viewer", ["posts.read"]),
            _role("editor", ["posts.write"], inherits=["viewer"]),
        )
        eff = resolve_effective_permissions("editor", roles)
        assert eff.direct == {"posts.write"}
        assert eff.inherited == {"posts.read": ("viewer",)}
        assert eff.ancestors == ("viewer",)
        assert eff.all_permissions == {"posts.read", "posts.write"}

    def test_deep_chain(self) -> None:
        roles = _index(
            _role("a", ["p.a"]),
            _role("b", ["p.b"], inherits=["a"]),
            _role("c", ["p.c"], inherits=["b"]),
        )
        eff = resolve_effective_permissions("c", roles)
        assert eff.all_permissions == {"p.a", "p.b", "p.c"}
        assert eff.inherited["p.a"] == ("a",)
        assert eff.ancestors == ("a", "b")


class TestProvenance:
    def test_diamond_records_both_sources(self) -> None:
        roles = _index(
            _role("base", ["p.shared"]),
            _role("left", ["p.shared", "p.left"], inherits=["base"]),
            _role("right", ["p.right"], inherits=["base"]),
            _role("top", [], inherits=["left", "right"]),
        )
        eff = resolve_effective_permissions("top", roles)
        assert eff.inherited["p.shared"] == ("base", "left")
        assert eff.ancestors == ("base", "left", "right")

    def test_direct_wins_over_inherited(self) -> None:
        roles = _index(
            _role("viewer", ["posts.read"]),
            _role("editor", ["posts.read", "posts.write"], inherits=["viewer"]),
        )
        eff = resolve_effective_permissions("editor", roles)
        assert "posts.read" in eff.direct
        assert "posts.read" not in eff.inherited


class TestCyclesAndMissing:
    def test_two_role_cycle_terminates(self) -> None:
        roles = _index(
            _role("a", ["p.a"], inherits=["b"]),
            _role("b", ["p.b"], inherits=["a"]),
        )
        eff = resolve_effective_permissions("a", roles)
        assert eff.all_permissions == {"p.a", "p.b"}
        assert eff.ancestors == ("b",)
        assert eff.missing == ()

    def test_self_reference_ignored(self) -> None:
        roles = _index(_role("a", ["p.a"], inherits=["a"]))
        eff = resolve_effective_permissions("a", roles)
        assert eff.direct == {"p.a"}
        assert eff.ancestors == ()

    def test_missing_parent_reported_and_grants_nothing(self) -> None:
        roles = _index(_role("editor", ["posts.write"], inherits=["ghost"]))
        eff = resolve_effective_permissions("editor", roles)
        assert eff.missing == ("ghost",)
        assert eff.all_permissions == {"posts.write"}
        assert eff.ancestors == ()

    def test_unknown_target_role(self) -> None:
        eff = resolve_effective_permissions("nope", {})
        assert eff == EffectivePermissions(role="nope", missing=("nope",))
        assert eff.all_permissions == frozenset()


class TestDuckTyping:
    def test_dict_roles_resolve_like_objects(self) -> None:
        roles = {
            "viewer": {"permissions": ["posts.read"], "inherits": []},
            "editor": {"permissions": ["posts.write"], "inherits": ["viewer"]},
        }
        eff = resolve_effective_permissions("editor", roles)
        assert eff.all_permissions == {"posts.read", "posts.write"}
        assert eff.inherited == {"posts.read": ("viewer",)}
