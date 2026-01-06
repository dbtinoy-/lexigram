"""Tests for PromptRegistry and VersionedPromptStore."""

from __future__ import annotations

import pytest

from lexigram.ai.prompt.exceptions import PromptNotFoundError, PromptVersionError
from lexigram.ai.prompt.registry.registry import PromptRegistry
from lexigram.ai.prompt.registry.versioned import VersionedPromptStore
from lexigram.ai.prompt.template.string import StringPromptTemplate
from lexigram.ai.prompt.variables.types import PromptVariable


def _make_tmpl(name: str, text: str = "Hello {x}") -> StringPromptTemplate:
    return StringPromptTemplate(name=name, template=text)


# ---------------------------------------------------------------------------
# PromptRegistry
# ---------------------------------------------------------------------------


def test_registry_register_and_get() -> None:
    reg = PromptRegistry()
    tmpl = _make_tmpl("hello")
    reg.register("hello", tmpl)
    assert reg.get("hello") is tmpl


def test_registry_get_not_found_raises() -> None:
    reg = PromptRegistry()
    with pytest.raises(PromptNotFoundError, match="hello"):
        reg.get("hello")


def test_registry_duplicate_raises() -> None:
    reg = PromptRegistry()
    tmpl = _make_tmpl("t")
    reg.register("t", tmpl)
    with pytest.raises(ValueError, match="already registered"):
        reg.register("t", tmpl)


def test_registry_overwrite_allowed() -> None:
    reg = PromptRegistry()
    t1 = _make_tmpl("t", "old")
    t2 = _make_tmpl("t", "new")
    reg.register("t", t1)
    reg.register("t", t2, overwrite=True)
    assert reg.get("t") is t2


def test_registry_list_names() -> None:
    reg = PromptRegistry()
    reg.register("b", _make_tmpl("b"))
    reg.register("a", _make_tmpl("a"))
    assert reg.list_names() == ["a", "b"]


def test_registry_unregister() -> None:
    reg = PromptRegistry()
    reg.register("t", _make_tmpl("t"))
    reg.unregister("t")
    assert "t" not in reg


def test_registry_unregister_not_found() -> None:
    reg = PromptRegistry()
    with pytest.raises(PromptNotFoundError):
        reg.unregister("ghost")


def test_registry_contains_and_len() -> None:
    reg = PromptRegistry()
    reg.register("a", _make_tmpl("a"))
    assert "a" in reg
    assert len(reg) == 1


# ---------------------------------------------------------------------------
# VersionedPromptStore
# ---------------------------------------------------------------------------


def test_versioned_push_and_get() -> None:
    store = VersionedPromptStore()
    t1 = _make_tmpl("t", "v1")
    v = store.push("t", t1)
    assert v == 1
    assert store.get("t") is t1


def test_versioned_push_increments_version() -> None:
    store = VersionedPromptStore()
    v1 = store.push("t", _make_tmpl("t", "v1"))
    v2 = store.push("t", _make_tmpl("t", "v2"))
    assert v1 == 1
    assert v2 == 2


def test_versioned_get_latest() -> None:
    store = VersionedPromptStore()
    store.push("t", _make_tmpl("t", "v1"))
    t2 = _make_tmpl("t", "v2")
    store.push("t", t2)
    assert store.get("t") is t2


def test_versioned_get_specific_version() -> None:
    store = VersionedPromptStore()
    t1 = _make_tmpl("t", "v1")
    t2 = _make_tmpl("t", "v2")
    store.push("t", t1)
    store.push("t", t2)
    assert store.get_version("t", 1) is t1
    assert store.get_version("t", 2) is t2


def test_versioned_rollback_one_step() -> None:
    store = VersionedPromptStore()
    t1 = _make_tmpl("t", "v1")
    t2 = _make_tmpl("t", "v2")
    store.push("t", t1)
    store.push("t", t2)
    restored = store.rollback("t")
    assert restored is t1
    assert store.get("t") is t1


def test_versioned_rollback_too_far_raises() -> None:
    store = VersionedPromptStore()
    store.push("t", _make_tmpl("t", "v1"))
    with pytest.raises(PromptVersionError):
        store.rollback("t", steps=5)


def test_versioned_get_unknown_raises() -> None:
    store = VersionedPromptStore()
    with pytest.raises(PromptNotFoundError):
        store.get("ghost")


def test_versioned_list_versions() -> None:
    store = VersionedPromptStore()
    store.push("t", _make_tmpl("t", "v1"), metadata={"author": "alice"})
    store.push("t", _make_tmpl("t", "v2"))
    versions = store.list_versions("t")
    assert len(versions) == 2
    assert versions[0]["version"] == 1
    assert versions[0]["metadata"] == {"author": "alice"}
    assert versions[1]["current"] is True


def test_versioned_max_versions_evicts_oldest() -> None:
    store = VersionedPromptStore(max_versions=2)
    store.push("t", _make_tmpl("t", "v1"))
    store.push("t", _make_tmpl("t", "v2"))
    store.push("t", _make_tmpl("t", "v3"))
    versions = store.list_versions("t")
    # version 1 was evicted
    assert versions[0]["version"] == 2
    assert len(versions) == 2


def test_versioned_get_evicted_version_raises() -> None:
    store = VersionedPromptStore(max_versions=1)
    store.push("t", _make_tmpl("t", "v1"))
    store.push("t", _make_tmpl("t", "v2"))
    with pytest.raises(PromptVersionError):
        store.get_version("t", 1)
