"""Builder edge validation tests (Task 2.7 / 4.3)."""

from __future__ import annotations

import pytest

from lexigram.nosql.exceptions import NoSQLFilterError
from lexigram.nosql.query.builder import DocumentQueryBuilder

_COMPARISON_CALLS = [
    ("where_ne", ("$foo", 1)),
    ("where_gt", ("$foo", 1)),
    ("where_gte", ("$foo", 1)),
    ("where_lt", ("$foo", 1)),
    ("where_lte", ("$foo", 1)),
    ("where_between", ("$foo", 1, 2)),
    ("where_in", ("$foo", [1])),
    ("where_not_in", ("$foo", [1])),
    ("where_exists", ("$foo",)),
    ("where_type", ("$foo", "int")),
]


class TestFieldRejection:
    """$``-prefixed fields are rejected at the fluent edge."""

    @pytest.mark.parametrize(
        ("method_name", "args", "kwargs"),
        [
            ("where", ("$where", "function(){...}"), {}),
            ("where", ("$expr", {"$eq": ["$a", 1]}), {}),
            ("where", ("$regex", "x"), {}),
            *[(name, args, {}) for name, args in _COMPARISON_CALLS],
        ],
    )
    def test_dollar_field_rejected(
        self,
        method_name: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> None:
        builder = DocumentQueryBuilder()
        with pytest.raises(NoSQLFilterError):
            getattr(builder, method_name)(*args, **kwargs)

    def test_where_regex_dollar_field_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            DocumentQueryBuilder().where_regex("$name", "x")


class TestRegexGate:
    """where_regex patterns and options must pass the shared shape gate."""

    def test_semicolon_pattern_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            DocumentQueryBuilder().where_regex("name", "a;b")

    def test_control_char_pattern_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            DocumentQueryBuilder().where_regex("name", "a\nb")

    def test_too_long_pattern_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            DocumentQueryBuilder().where_regex("name", "a" * 2048)

    def test_bad_options_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            DocumentQueryBuilder().where_regex("name", "a", "k")

    def test_valid_regex_builds_unchanged(self) -> None:
        query = DocumentQueryBuilder().where_regex("name", "^J", "i").build()
        assert query.filter == {"name": {"$regex": "^J", "$options": "i"}}


class TestCombinatorValidation:
    """and_where / or_where validate conditions at insertion."""

    def test_and_where_where_operator_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            DocumentQueryBuilder().and_where({"$where": "..."})

    def test_and_where_unsafe_regex_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            DocumentQueryBuilder().and_where({"password": {"$regex": "a;b"}})

    def test_or_where_unsafe_regex_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            DocumentQueryBuilder().or_where({"password": {"$regex": "a;b"}})

    def test_and_where_does_not_mutate_on_rejection(self) -> None:
        builder = DocumentQueryBuilder().where("status", "active")
        with pytest.raises(NoSQLFilterError):
            builder.and_where({"$where": "..."})
        assert builder.build().filter == {"status": "active"}

    def test_valid_conditions_build(self) -> None:
        query = (
            DocumentQueryBuilder()
            .and_where({"status": "active"}, {"age": {"$gt": 18}})
            .build()
        )
        assert query.filter == {
            "$and": [{"status": "active"}, {"age": {"$gt": 18}}],
        }


class TestTextGate:
    """where_text requires a non-empty string."""

    def test_empty_search_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            DocumentQueryBuilder().where_text("")

    def test_non_string_search_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            DocumentQueryBuilder().where_text(5)  # type: ignore[arg-type]

    def test_valid_search_builds(self) -> None:
        query = DocumentQueryBuilder().where_text("hello world").build()
        assert query.filter == {"$text": {"$search": "hello world"}}


class TestExistingOutputsUnchanged:
    """Builder outputs for legitimate inputs are unchanged."""

    def test_where_ne_output(self) -> None:
        query = DocumentQueryBuilder().where_ne("status", "deleted").build()
        assert query.filter == {"status": {"$ne": "deleted"}}

    def test_where_between_output(self) -> None:
        query = DocumentQueryBuilder().where_between("age", 18, 65).build()
        assert query.filter == {"age": {"$gte": 18, "$lte": 65}}

    def test_where_in_output(self) -> None:
        query = DocumentQueryBuilder().where_in("role", ["admin", "mod"]).build()
        assert query.filter == {"role": {"$in": ["admin", "mod"]}}