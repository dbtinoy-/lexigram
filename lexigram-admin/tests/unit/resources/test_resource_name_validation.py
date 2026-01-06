"""Tests for Resource name slug validation."""

from __future__ import annotations

import pytest

from lexigram.admin.resources.base import Resource


class TestResourceNameValidation:
    def test_name_none_passes(self) -> None:
        class _Res(Resource):
            pass

    def test_valid_slug_passes(self) -> None:
        class _Res(Resource):
            name = "users"

    def test_valid_dotted_slug_passes(self) -> None:
        class _Res(Resource):
            name = "fake_pkg.users"

    def test_valid_name_with_underscore_passes(self) -> None:
        class _Res(Resource):
            name = "active_users"

    def test_name_with_hyphen_raises(self) -> None:
        with pytest.raises(ValueError, match="not a valid slug"):

            class _Res(Resource):  # type: ignore[misc]
                name = "bad-name"

    def test_name_with_uppercase_raises(self) -> None:
        with pytest.raises(ValueError, match="not a valid slug"):

            class _Res(Resource):  # type: ignore[misc]
                name = "BadName"

    def test_name_with_space_raises(self) -> None:
        with pytest.raises(ValueError, match="not a valid slug"):

            class _Res(Resource):  # type: ignore[misc]
                name = "bad name"

    def test_name_starting_with_number_raises(self) -> None:
        with pytest.raises(ValueError, match="not a valid slug"):

            class _Res(Resource):  # type: ignore[misc]
                name = "2nd_resource"

    def test_name_emtpy_string_raises(self) -> None:
        with pytest.raises(ValueError, match="not a valid slug"):

            class _Res(Resource):  # type: ignore[misc]
                name = ""


