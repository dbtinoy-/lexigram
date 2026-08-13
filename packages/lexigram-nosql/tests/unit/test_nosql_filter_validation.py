"""Unit tests for the NoSQL filter validator (Task 1.7 / 4.1)."""

from __future__ import annotations

import pytest

from lexigram.nosql.exceptions import NoSQLFilterError
from lexigram.nosql.security import validate_filter


class TestDeniedOperators:
    """Operators denied in any position."""

    def test_where_top_level_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"$where": "return true"})

    def test_expr_top_level_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"$expr": {"$eq": ["$a", 1]}})

    def test_mod_top_level_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"$mod": [4, 0]})

    def test_mod_nested_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"count": {"$mod": [4, 0]}})

    def test_function_nested_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"field": {"$function": {"body": "x"}}})

    def test_accumulator_nested_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"field": {"$accumulator": {"init": "x"}}})

    def test_expr_nested_in_operand_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"user": {"$eq": {"$expr": {"$eq": ["$a", 1]}}}})

    def test_expr_deep_in_list_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"roles": {"$in": [{"$where": "x"}, "admin"]}})


class TestAllowlistPositionRules:
    """Top-level vs nested operator positions."""

    def test_safe_filter_passes(self) -> None:
        result = validate_filter({"status": "active", "age": {"$gte": 18}})
        assert result == {"status": "active", "age": {"$gte": 18}}

    def test_and_combinator_passes(self) -> None:
        filter = {"$and": [{"status": "active"}, {"age": {"$lte": 65}}]}
        assert validate_filter(filter) == filter

    def test_or_combinator_passes(self) -> None:
        filter = {"$or": [{"role": "admin"}, {"role": "moderator"}]}
        assert validate_filter(filter) == filter

    def test_nor_combinator_passes(self) -> None:
        filter = {"$nor": [{"status": "deleted"}, {"status": "banned"}]}
        assert validate_filter(filter) == filter

    def test_not_top_level_passes(self) -> None:
        filter = {"$not": {"$gt": 5}}
        assert validate_filter(filter) == filter

    def test_ne_top_level_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"$ne": ""})

    def test_ne_nested_allowed(self) -> None:
        filter = {"password": {"$ne": ""}}
        assert validate_filter(filter) == filter

    def test_regex_top_level_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"$regex": ".*"})

    def test_unknown_top_level_operator_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"$evil": 1})

    def test_unknown_nested_operator_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"age": {"$existsy": True}})

    def test_options_without_regex_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"name": {"$options": "i"}})

    def test_embedded_document_match_passes(self) -> None:
        filter = {"address": {"city": "Paris", "zip": {"$ne": "0"}}}
        assert validate_filter(filter) == filter


class TestTextShape:
    """$text query shape gate."""

    def test_text_search_str_passes(self) -> None:
        filter = {"$text": {"$search": "term"}}
        assert validate_filter(filter) == filter

    def test_text_search_non_string_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"$text": {"$search": 5}})

    def test_text_search_empty_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"$text": {"$search": ""}})

    def test_text_non_dict_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"$text": "term"})

    def test_text_language_allowed_passes(self) -> None:
        filter = {"$text": {"$search": "term", "$language": "french"}}
        assert validate_filter(filter) == filter

    def test_text_language_unsupported_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"$text": {"$search": "term", "$language": "klingon"}})

    def test_text_extra_key_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"$text": {"$search": "term", "$caseSensitive": True}})

    def test_text_nested_position_passes(self) -> None:
        filter = {"body": {"$text": {"$search": "term"}}}
        assert validate_filter(filter) == filter


class TestRegexShape:
    """$regex shape gate (shared with the builder)."""

    def test_regex_with_options_passes(self) -> None:
        filter = {"name": {"$regex": "^J", "$options": "i"}}
        assert validate_filter(filter) == filter

    def test_regex_without_options_passes(self) -> None:
        filter = {"name": {"$regex": "J"}}
        assert validate_filter(filter) == filter

    def test_regex_semicolon_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"name": {"$regex": "a;b"}})

    def test_regex_control_char_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"name": {"$regex": "a\nb"}})

    def test_regex_too_long_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"name": {"$regex": "a" * 2048}})

    def test_regex_bad_options_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"name": {"$regex": "a", "$options": "k"}})

    def test_regex_empty_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"name": {"$regex": ""}})


class TestFieldNameIdentifiers:
    """Plain field name identifier pattern."""

    def test_dotted_field_passes(self) -> None:
        filter = {"user.name": "Alice"}
        assert validate_filter(filter) == filter

    def test_field_with_space_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"a b": 1})

    def test_field_with_slash_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"a/b": 1})

    def test_dollar_prefixed_key_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({"$where_user": 1})

    def test_empty_filter_passes(self) -> None:
        assert validate_filter({}) == {}

    def test_non_mapping_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter(["status"])  # type: ignore[arg-type]

    def test_non_string_key_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            validate_filter({1: "x"})  # type: ignore[dict-item]