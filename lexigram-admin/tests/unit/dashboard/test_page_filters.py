"""Tests for page-level dashboard filter state and form rendering."""

from __future__ import annotations

from typing import Any

from lexigram.admin.dashboard.page_filters import (
    applied_from_query,
    clear_page_filters,
    read_page_filters,
    render_page_filter_form,
    save_page_filters,
    widget_fetch_url,
)
from lexigram.contracts.admin.types import PageFilterField

SCHEMA = [
    PageFilterField(
        name="period",
        type="select",
        label="Period",
        options=(("30d", "Last 30 days"), ("90d", "Last 90 days")),
        default="30d",
    ),
    PageFilterField(name="min", type="number", label="Min", default=5),
    PageFilterField(name="active", type="boolean", label="Active only"),
]


class FakeSession(dict[str, Any]):
    """Minimal session facade (dict) with Starlette-style access."""


class FakeRequest:
    """Minimal request with query_params and optional session."""

    def __init__(
        self, params: dict[str, str], session: FakeSession | None = None
    ) -> None:
        self.query_params = dict(params)
        self.session = session


class TestReadPageFilters:
    def test_defaults_only(self) -> None:
        result = read_page_filters(FakeRequest({}), "dash", SCHEMA)
        assert result == {"period": "30d", "min": 5}

    def test_query_overrides_defaults_with_coercion(self) -> None:
        request = FakeRequest({"period": "90d", "min": "10", "active": "on"})
        result = read_page_filters(request, "dash", SCHEMA)
        assert result["period"] == "90d"
        assert result["min"] == 10
        assert result["active"] is True

    def test_boolean_false_forms(self) -> None:
        assert (
            read_page_filters(FakeRequest({"active": "0"}), "dash", SCHEMA)["active"]
            is False
        )

    def test_non_numeric_number_stays_string(self) -> None:
        result = read_page_filters(FakeRequest({"min": "abc"}), "dash", SCHEMA)
        assert result["min"] == "abc"

    def test_session_state_merged_query_wins(self) -> None:
        session = FakeSession({"admin_page_filters.dash": {"period": "30d", "min": 5}})
        result = read_page_filters(
            FakeRequest({"period": "90d"}, session=session), "dash", SCHEMA
        )
        assert result == {"period": "90d", "min": 5}

    def test_unknown_session_keys_ignored(self) -> None:
        session = FakeSession({"admin_page_filters.dash": {"nope": "x"}})
        result = read_page_filters(FakeRequest({}, session=session), "dash", SCHEMA)
        assert "nope" not in result

    def test_reset_param_clears_session_and_returns_defaults(self) -> None:
        session = FakeSession({"admin_page_filters.dash": {"period": "90d", "min": 10}})
        result = read_page_filters(
            FakeRequest({"reset_page_filters": "1"}, session=session), "dash", SCHEMA
        )
        assert result == {"period": "30d", "min": 5}
        assert "admin_page_filters.dash" not in session

    def test_no_session_supported(self) -> None:
        result = read_page_filters(FakeRequest({"period": "90d"}), "dash", SCHEMA)
        assert result["period"] == "90d"


class TestPersistPageFilters:
    def test_save_clear_round_trip(self) -> None:
        session = FakeSession()
        request = FakeRequest({}, session=session)
        save_page_filters(request, "dash", {"period": "90d"})
        assert session["admin_page_filters.dash"] == {"period": "90d"}
        clear_page_filters(request, "dash")
        assert "admin_page_filters.dash" not in session

    def test_save_noop_without_session(self) -> None:
        save_page_filters(FakeRequest({}), "dash", {"period": "90d"})  # must not raise


class TestAppliedFromQuery:
    def test_true_when_filter_param_present(self) -> None:
        assert applied_from_query(FakeRequest({"period": "90d"}), SCHEMA) is True

    def test_false_when_only_other_params(self) -> None:
        assert applied_from_query(FakeRequest({"id": "default"}), SCHEMA) is False


class TestWidgetFetchUrl:
    def test_annotates_endpoint(self) -> None:
        url = widget_fetch_url("/api/w", {"period": "90d", "active": True})
        assert url == "/api/w?period=90d&active=True"

    def test_preserves_existing_query(self) -> None:
        url = widget_fetch_url("/api/w?x=1", {"period": "90d"})
        assert url == "/api/w?x=1&period=90d"

    def test_none_and_empty_unchanged(self) -> None:
        assert widget_fetch_url("/api/w", None) == "/api/w"
        assert widget_fetch_url("/api/w", {}) == "/api/w"

    def test_empty_values_dropped(self) -> None:
        url = widget_fetch_url("/api/w", {"period": "90d", "q": "", "n": None})
        assert url == "/api/w?period=90d"


class TestRenderPageFilterForm:
    def test_none_when_no_schema(self) -> None:
        assert render_page_filter_form([], {}, "/admin/") is None

    def test_renders_fields_with_current_values(self) -> None:
        html = str(
            render_page_filter_form(
                SCHEMA, {"period": "90d", "min": 7, "active": True}, "/admin/"
            )
        )
        assert '<form method="get" action="/admin/"' in html
        assert 'name="period"' in html
        assert '<option value="90d" selected>Last 90 days</option>' in html
        assert 'value="7"' in html
        assert "checked" in html

    def test_renders_apply_and_reset(self) -> None:
        html = str(render_page_filter_form(SCHEMA, {}, "/admin/"))
        assert 'type="submit"' in html
        assert "reset_page_filters=1" in html
