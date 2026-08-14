"""Verify deprecation shims and Resource.fields integration."""

from __future__ import annotations

import importlib
import pathlib
import sys
import warnings

import pytest

from lexigram.admin.resources.base import Resource
from lexigram.admin.schema import BooleanField, TextField
from lexigram.ui.columns.types import TextColumn


class TestDeprecationWarnings:
    """No deprecated API modules remain — all deprecation shims removed."""


class TestResourceFields:
    """Test Resource.fields attribute and backward-compat derivation."""

    def test_fields_defaults_to_empty(self) -> None:
        assert Resource.fields == []

    def test_fields_derives_columns(self) -> None:
        class TestRes(Resource):
            fields = [TextField(name="name"), BooleanField(name="active")]

        assert list(TestRes.columns) == TestRes.fields

    def test_fields_derives_filters(self) -> None:
        class TestRes(Resource):
            fields = [TextField(name="name"), BooleanField(name="active")]

        assert len(TestRes.filters) == 2
        assert all(getattr(f, "filterable", False) for f in TestRes.filters)

    def test_warns_when_mixing_with_columns(self) -> None:
        with pytest.warns(DeprecationWarning, match="fields is the new"):
            class TestRes(Resource):  # noqa: F841
                fields = [TextField(name="name")]
                columns = [TextColumn("name")]

    def test_warns_when_mixing_with_filters(self) -> None:
        with pytest.warns(DeprecationWarning, match="fields is the new"):
            class TestRes(Resource):  # noqa: F841
                fields = [TextField(name="name")]
                filters = []

    def test_warns_when_mixing_with_form_class(self) -> None:
        with pytest.warns(DeprecationWarning, match="fields is the new"):
            class TestRes(Resource):  # noqa: F841
                fields = [TextField(name="name")]
                form_class = object

    def test_does_not_warn_when_only_fields(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            class TestRes(Resource):  # noqa: F841
                fields = [TextField(name="name")]

    def test_columns_not_overridden_when_explicitly_set(self) -> None:
        with pytest.warns(DeprecationWarning):
            class TestRes(Resource):  # noqa: F841
                fields = [TextField(name="name")]
                columns = [TextColumn("name")]

        assert len(TestRes.columns) == 1
        assert isinstance(TestRes.columns[0], TextColumn)
