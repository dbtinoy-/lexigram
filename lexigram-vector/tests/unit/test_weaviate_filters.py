"""Unit tests for WeaviateFilterCompiler."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub weaviate.classes.query before importing the compiler so the lazy
# `import weaviate.classes.query as wq` inside _visit_* resolves without
# the real package installed.
#
# IMPORTANT: Python resolves `import a.b.c as x` by walking the attribute
# chain on sys.modules["a"], so we must set the attributes on the parent
# stub AND register all three levels in sys.modules.
# ---------------------------------------------------------------------------

_weaviate_stub = MagicMock()
_wq_stub = MagicMock()

# Wire the attribute chain so `import weaviate.classes.query as wq`
# gives back exactly `_wq_stub`.
_weaviate_stub.classes.query = _wq_stub

sys.modules["weaviate"] = _weaviate_stub
sys.modules["weaviate.classes"] = _weaviate_stub.classes
sys.modules["weaviate.classes.query"] = _wq_stub

from lexigram.contracts.data.vector.filters import (  # noqa: E402
    Filter,
    FilterOperator,
    LogicalOperator,
    MetadataCondition,
    MetadataConditionGroup,
)
from lexigram.vector.backends.weaviate.filters import WeaviateFilterCompiler  # noqa: E402
from lexigram.vector.exceptions import FilterCompilationError  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_prop_builder() -> MagicMock:
    """Return a fresh prop builder and re-wire Filter.by_property."""
    prop = MagicMock(name="prop_builder")
    _wq_stub.Filter.by_property.return_value = prop
    return prop


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWeaviateFilterCompiler:
    def setup_method(self) -> None:
        """Reset stubs between tests."""
        _wq_stub.Filter.by_property.reset_mock()
        _wq_stub.Filter.all_of.reset_mock()
        _wq_stub.Filter.any_of.reset_mock()

    # ------------------------------------------------------------------
    # Single condition tests
    # ------------------------------------------------------------------

    def test_compile_eq_condition(self) -> None:
        prop = _fresh_prop_builder()
        condition = Filter.eq("category", "science")
        compiler = WeaviateFilterCompiler()

        compiler.compile(condition)

        _wq_stub.Filter.by_property.assert_called_once_with("category")
        prop.equal.assert_called_once_with("science")

    def test_compile_ne_condition(self) -> None:
        prop = _fresh_prop_builder()
        condition = Filter.ne("status", "deleted")
        compiler = WeaviateFilterCompiler()

        compiler.compile(condition)

        prop.not_equal.assert_called_once_with("deleted")

    def test_compile_gt_condition(self) -> None:
        prop = _fresh_prop_builder()
        condition = Filter.gt("year", 2020)
        compiler = WeaviateFilterCompiler()

        compiler.compile(condition)

        prop.greater_than.assert_called_once_with(2020)

    def test_compile_gte_condition(self) -> None:
        prop = _fresh_prop_builder()
        condition = Filter.gte("score", 0.8)
        compiler = WeaviateFilterCompiler()

        compiler.compile(condition)

        prop.greater_or_equal.assert_called_once_with(0.8)

    def test_compile_lt_condition(self) -> None:
        prop = _fresh_prop_builder()
        condition = Filter.lt("count", 100)
        compiler = WeaviateFilterCompiler()

        compiler.compile(condition)

        prop.less_than.assert_called_once_with(100)

    def test_compile_lte_condition(self) -> None:
        prop = _fresh_prop_builder()
        condition = Filter.lte("price", 50.0)
        compiler = WeaviateFilterCompiler()

        compiler.compile(condition)

        prop.less_or_equal.assert_called_once_with(50.0)

    def test_compile_in_operator(self) -> None:
        prop = _fresh_prop_builder()
        condition = Filter.in_("tag", ["a", "b", "c"])
        compiler = WeaviateFilterCompiler()

        compiler.compile(condition)

        prop.contains_any.assert_called_once_with(["a", "b", "c"])

    def test_compile_contains_operator(self) -> None:
        prop = _fresh_prop_builder()
        condition = Filter.contains("title", "python")
        compiler = WeaviateFilterCompiler()

        compiler.compile(condition)

        prop.like.assert_called_once_with("*python*")

    def test_compile_exists_true(self) -> None:
        prop = _fresh_prop_builder()
        condition = Filter.exists("metadata_key", True)
        compiler = WeaviateFilterCompiler()

        compiler.compile(condition)

        # exists=True → is_none(False)
        prop.is_none.assert_called_once_with(False)

    def test_compile_exists_false(self) -> None:
        prop = _fresh_prop_builder()
        condition = Filter.exists("metadata_key", False)
        compiler = WeaviateFilterCompiler()

        compiler.compile(condition)

        # exists=False → is_none(True)
        prop.is_none.assert_called_once_with(True)

    # ------------------------------------------------------------------
    # Group tests
    # ------------------------------------------------------------------

    def test_compile_and_group(self) -> None:
        prop1 = MagicMock(name="prop1")
        prop2 = MagicMock(name="prop2")
        _wq_stub.Filter.by_property.side_effect = [prop1, prop2]

        group = Filter.and_(
            Filter.eq("category", "science"),
            Filter.gte("year", 2020),
        )
        compiler = WeaviateFilterCompiler()

        compiler.compile(group)

        assert _wq_stub.Filter.all_of.called
        call_args = _wq_stub.Filter.all_of.call_args[0][0]
        assert len(call_args) == 2

    def test_compile_or_group(self) -> None:
        prop1 = MagicMock(name="prop1")
        prop2 = MagicMock(name="prop2")
        _wq_stub.Filter.by_property.side_effect = [prop1, prop2]

        group = Filter.or_(
            Filter.eq("status", "published"),
            Filter.eq("status", "preprint"),
        )
        compiler = WeaviateFilterCompiler()

        compiler.compile(group)

        assert _wq_stub.Filter.any_of.called
        call_args = _wq_stub.Filter.any_of.call_args[0][0]
        assert len(call_args) == 2

    def test_compile_nested_group(self) -> None:
        """AND group with a nested OR group."""
        props = [MagicMock(name=f"prop{i}") for i in range(3)]
        _wq_stub.Filter.by_property.side_effect = props

        nested = Filter.and_(
            Filter.eq("active", True),
            Filter.or_(
                Filter.eq("tier", "gold"),
                Filter.eq("tier", "platinum"),
            ),
        )
        compiler = WeaviateFilterCompiler()
        compiler.compile(nested)

        # OR group compiled first, AND group wraps it
        assert _wq_stub.Filter.any_of.called
        assert _wq_stub.Filter.all_of.called

    # ------------------------------------------------------------------
    # Unsupported operator
    # ------------------------------------------------------------------

    def test_unsupported_operator_raises(self) -> None:
        _fresh_prop_builder()
        condition = MetadataCondition(
            field="tags",
            operator=FilterOperator.NOT_IN,
            value=["x", "y"],
        )
        compiler = WeaviateFilterCompiler()

        with pytest.raises(FilterCompilationError):
            compiler.compile(condition)
