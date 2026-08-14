"""Tests for admin testing utilities (meta-tests)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.testing import (
    AdminResponse,
    AdminTestClient,
    assert_result_err,
    assert_result_ok,
    make_resource_record,
)

# ---------------------------------------------------------------------------
# AdminResponse
# ---------------------------------------------------------------------------

class TestAdminResponse:
    def test_is_htmx_redirect_true(self) -> None:
        resp = AdminResponse(status_code=200, headers={"HX-Redirect": "/admin/user"})
        assert resp.is_htmx_redirect() is True

    def test_is_htmx_redirect_false(self) -> None:
        resp = AdminResponse(status_code=302)
        assert resp.is_htmx_redirect() is False

    def test_htmx_redirect_url(self) -> None:
        resp = AdminResponse(status_code=200, headers={"HX-Redirect": "/admin/user"})
        assert resp.htmx_redirect_url() == "/admin/user"

    def test_htmx_redirect_url_none(self) -> None:
        resp = AdminResponse(status_code=200)
        assert resp.htmx_redirect_url() is None

    def test_htmx_trigger(self) -> None:
        resp = AdminResponse(status_code=200, headers={"HX-Trigger": "refresh-list"})
        assert resp.htmx_trigger() == "refresh-list"


# ---------------------------------------------------------------------------
# AdminTestClient URL builder
# ---------------------------------------------------------------------------

class TestAdminTestClientUrl:
    def _client(self) -> AdminTestClient:
        return AdminTestClient(MagicMock(), prefix="/admin")

    def test_url_list(self) -> None:
        c = self._client()
        assert c.url("user") == "/admin/user"

    def test_url_detail(self) -> None:
        c = self._client()
        assert c.url("user", "123") == "/admin/user/123"

    def test_url_nested(self) -> None:
        c = self._client()
        assert c.url("user", "123", "edit") == "/admin/user/123/edit"

    def test_custom_prefix(self) -> None:
        c = AdminTestClient(MagicMock(), prefix="/cms")
        assert c.url("post") == "/cms/post"


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------

class TestAssertions:
    def test_assert_status_passes(self) -> None:
        resp = AdminResponse(status_code=200)
        AdminTestClient.assert_status(resp, 200)

    def test_assert_status_fails(self) -> None:
        resp = AdminResponse(status_code=404)
        with pytest.raises(AssertionError):
            AdminTestClient.assert_status(resp, 200)

    def test_assert_ok_passes(self) -> None:
        resp = AdminResponse(status_code=200, text="<html>ok</html>")
        AdminTestClient.assert_ok(resp)

    def test_assert_redirect_htmx(self) -> None:
        resp = AdminResponse(status_code=200, headers={"HX-Redirect": "/admin/user"})
        AdminTestClient.assert_redirect(resp)

    def test_assert_redirect_standard_302(self) -> None:
        resp = AdminResponse(status_code=302)
        AdminTestClient.assert_redirect(resp)

    def test_assert_redirect_fails_on_200_no_header(self) -> None:
        resp = AdminResponse(status_code=200)
        with pytest.raises(AssertionError):
            AdminTestClient.assert_redirect(resp)

    def test_assert_unprocessable(self) -> None:
        resp = AdminResponse(status_code=422)
        AdminTestClient.assert_unprocessable(resp)

    def test_assert_contains_passes(self) -> None:
        resp = AdminResponse(status_code=200, text="<h1>Welcome</h1>")
        AdminTestClient.assert_contains(resp, "Welcome")

    def test_assert_contains_fails(self) -> None:
        resp = AdminResponse(status_code=200, text="<h1>Hello</h1>")
        with pytest.raises(AssertionError):
            AdminTestClient.assert_contains(resp, "Goodbye")

    def test_assert_htmx_trigger(self) -> None:
        resp = AdminResponse(status_code=200, headers={"HX-Trigger": "refresh-list,toast"})
        AdminTestClient.assert_htmx_trigger(resp, "refresh-list")

    def test_assert_htmx_trigger_fails(self) -> None:
        resp = AdminResponse(status_code=200, headers={"HX-Trigger": "other-event"})
        with pytest.raises(AssertionError):
            AdminTestClient.assert_htmx_trigger(resp, "refresh-list")


# ---------------------------------------------------------------------------
# make_resource_record
# ---------------------------------------------------------------------------

class TestMakeResourceRecord:
    def test_has_id(self) -> None:
        record = make_resource_record()
        assert "id" in record
        assert record["id"]

    def test_type_field(self) -> None:
        record = make_resource_record("user")
        assert record["_type"] == "user"

    def test_custom_fields_override(self) -> None:
        record = make_resource_record("user", name="Alice", email="a@b.com")
        assert record["name"] == "Alice"
        assert record["email"] == "a@b.com"

    def test_custom_id(self) -> None:
        record = make_resource_record(id="custom-id")
        assert record["id"] == "custom-id"

    def test_has_timestamps(self) -> None:
        record = make_resource_record()
        assert "created_at" in record
        assert "updated_at" in record


# ---------------------------------------------------------------------------
# Result assertion helpers
# ---------------------------------------------------------------------------

class TestResultAssertions:
    def _make_ok(self, value: object) -> object:
        m = MagicMock()
        m.is_ok.return_value = True
        m.is_err.return_value = False
        m.unwrap.return_value = value
        return m

    def _make_err(self, error: object) -> object:
        m = MagicMock()
        m.is_ok.return_value = False
        m.is_err.return_value = True
        m.unwrap_err.return_value = error
        return m

    def test_assert_result_ok_passes(self) -> None:
        result = self._make_ok("user-object")
        value = assert_result_ok(result)
        assert value == "user-object"

    def test_assert_result_ok_fails_on_err(self) -> None:
        result = self._make_err("error")
        with pytest.raises(AssertionError):
            assert_result_ok(result)

    def test_assert_result_err_passes(self) -> None:
        result = self._make_err("not-found")
        error = assert_result_err(result)
        assert error == "not-found"

    def test_assert_result_err_fails_on_ok(self) -> None:
        result = self._make_ok("value")
        with pytest.raises(AssertionError):
            assert_result_err(result)

