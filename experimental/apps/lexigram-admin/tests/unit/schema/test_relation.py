from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.schema import FieldError, SchemaField
from lexigram.admin.schema.relation import (
    BelongsToField,
    HasManyField,
    MorphField,
    RelationField,
)
from lexigram.result import Ok
from lexigram.ui import Element


class TestRelationField:
    def test_construct_with_resource(self) -> None:
        field = RelationField(name="user_id", resource="users")
        assert field.name == "user_id"
        assert field.resource == "users"

    def test_construct_with_searchable(self) -> None:
        field = RelationField(name="user_id", resource="users", searchable=True)
        assert field.searchable is True

    def test_render_form_returns_element(self) -> None:
        field = RelationField(name="user_id", resource="users")
        element = field.render_form("1")
        assert isinstance(element, Element)

    def test_from_form_valid(self) -> None:
        field = RelationField(name="user_id", resource="users")
        result = field.from_form("1")
        assert isinstance(result, Ok)
        assert result.unwrap() == "1"

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = RelationField(name="user_id", resource="users", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_is_schema_field(self) -> None:
        field = RelationField(name="user_id", resource="users")
        assert isinstance(field, SchemaField)


class TestBelongsToField:
    def test_construct_with_resource(self) -> None:
        field = BelongsToField(name="user_id", resource="users")
        assert field.name == "user_id"
        assert field.resource == "users"

    def test_construct_searchable(self) -> None:
        field = BelongsToField(name="user_id", resource="users", searchable=True)
        assert field.searchable is True
        assert field.resource == "users"

    def test_render_form_returns_element(self) -> None:
        field = BelongsToField(name="user_id", resource="users")
        element = field.render_form("1")
        assert isinstance(element, Element)

    def test_from_form_valid(self) -> None:
        field = BelongsToField(name="user_id", resource="users")
        result = field.from_form("1")
        assert isinstance(result, Ok)
        assert result.unwrap() == "1"

    def test_render_column_with_value(self) -> None:
        field = BelongsToField(name="user_id", resource="users")
        element = field.render_column(None, "1")
        output = str(element)
        assert "1" in output

    def test_render_column_with_none(self) -> None:
        field = BelongsToField(name="user_id", resource="users")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_is_schema_field(self) -> None:
        field = BelongsToField(name="user_id", resource="users")
        assert isinstance(field, SchemaField)


class TestHasManyField:
    def test_construct_with_options(self) -> None:
        options = [("1", "User 1"), ("2", "User 2")]
        field = HasManyField(name="user_ids", resource="users", options=options)
        assert field.options == options

    def test_render_form_returns_element(self) -> None:
        field = HasManyField(name="user_ids", resource="users")
        element = field.render_form(["1"])
        assert isinstance(element, Element)

    def test_from_form_returns_list(self) -> None:
        field = HasManyField(name="user_ids", resource="users")
        result = field.from_form("1,2")
        assert isinstance(result, Ok)
        assert result.unwrap() == ["1", "2"]

    def test_from_form_none_returns_none(self) -> None:
        field = HasManyField(name="user_ids", resource="users")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_render_column_shows_count(self) -> None:
        field = HasManyField(name="user_ids", resource="users")
        element = field.render_column(None, ["1", "2", "3"])
        output = str(element)
        assert "3" in output
        assert "items" in output

    def test_render_column_single_item(self) -> None:
        field = HasManyField(name="user_ids", resource="users")
        element = field.render_column(None, ["1"])
        output = str(element)
        assert "1" in output
        assert "item" in output

    def test_render_column_with_none(self) -> None:
        field = HasManyField(name="user_ids", resource="users")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_is_schema_field(self) -> None:
        field = HasManyField(name="user_ids", resource="users")
        assert isinstance(field, SchemaField)


class TestMorphField:
    def test_construct_with_morph_types(self) -> None:
        types = [("App\\Models\\Post", "Post"), ("App\\Models\\Page", "Page")]
        field = MorphField(
            name="taggable",
            resource="*",
            morph_types=types,
        )
        assert field.morph_types == types

    def test_render_form_returns_element(self) -> None:
        types = [("App\\Models\\Post", "Post")]
        field = MorphField(name="taggable", resource="*", morph_types=types)
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_from_form_valid(self) -> None:
        types = [("App\\Models\\Post", "Post")]
        field = MorphField(name="taggable", resource="*", morph_types=types)
        result = field.from_form("1")
        assert isinstance(result, Ok)
        assert result.unwrap() == "1"

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        types = [("App\\Models\\Post", "Post")]
        field = MorphField(
            name="taggable", resource="*", morph_types=types, nullable=True
        )
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_render_column_with_value(self) -> None:
        types = [("App\\Models\\Post", "Post")]
        field = MorphField(name="taggable", resource="*", morph_types=types)
        element = field.render_column(None, "1")
        output = str(element)
        assert "1" in output

    def test_render_column_with_none(self) -> None:
        types = [("App\\Models\\Post", "Post")]
        field = MorphField(name="taggable", resource="*", morph_types=types)
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_is_schema_field(self) -> None:
        types = [("App\\Models\\Post", "Post")]
        field = MorphField(name="taggable", resource="*", morph_types=types)
        assert isinstance(field, SchemaField)
