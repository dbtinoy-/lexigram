"""Tests for trash tab (include_deleted) in the admin list view."""
from __future__ import annotations

from lexigram.admin.ui.state import TableState


class TestTableStateIncludeDeleted:
    def test_default_is_false(self) -> None:
        state = TableState()
        assert state.include_deleted is False

    def test_with_include_deleted_true(self) -> None:
        state = TableState()
        new_state = state.with_include_deleted(True)
        assert new_state.include_deleted is True
        assert state.include_deleted is False  # immutability
        assert new_state.page == 1

    def test_with_include_deleted_false(self) -> None:
        state = TableState(include_deleted=True)
        new_state = state.with_include_deleted(False)
        assert new_state.include_deleted is False

    def test_to_query_params_includes(self) -> None:
        state = TableState(include_deleted=True)
        params = state.to_query_params()
        assert params.get("include_deleted") is True

    def test_to_query_params_omits_default(self) -> None:
        state = TableState()
        params = state.to_query_params()
        assert "include_deleted" not in params

    def test_from_request_parses_true(self) -> None:
        class FakeRequest:
            query_params = {"include_deleted": "true"}
        state = TableState.from_request(FakeRequest())
        assert state.include_deleted is True

    def test_from_request_parses_false(self) -> None:
        class FakeRequest:
            query_params = {}
        state = TableState.from_request(FakeRequest())
        assert state.include_deleted is False

    def test_to_url_includes_param(self) -> None:
        state = TableState(include_deleted=True)
        url = state.to_url("/admin/users")
        assert "include_deleted=True" in url

    def test_to_url_omits_default(self) -> None:
        state = TableState()
        url = state.to_url("/admin/users")
        assert "include_deleted" not in url
