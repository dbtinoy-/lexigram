"""Focused tests for the DataTable TableState."""

from __future__ import annotations

from typing import Any

from lexigram.ui.state import TableState


class _Q:
    def __init__(self, params: dict[str, str | list[str]]) -> None:
        self._params = params

    def get(self, key: str, default: Any = None) -> Any:
        value = self._params.get(key)
        if isinstance(value, list):
            return value[-1] if value else default
        return value if value is not None else default

    def getlist(self, key: str) -> list[str]:
        value = self._params.get(key)
        return value if isinstance(value, list) else ([value] if value is not None else [])

    def __iter__(self):
        return iter(self._params)


class _Req:
    def __init__(self, params: dict[str, str | list[str]]) -> None:
        self.query_params = _Q(params)


class TestFromRequest:
    def test_defaults(self) -> None:
        state = TableState.from_request(_Req({}))
        assert state.search == ""
        assert state.sort_order == "asc"
        assert state.page == 1
        assert state.per_page == 20
        assert state.view == "tabular"
        assert state.layout == "stack"
        assert state.include_deleted is False

    def test_standard_fields(self) -> None:
        state = TableState.from_request(
            _Req(
                {
                    "search": "bob",
                    "sort_by": "name",
                    "sort_order": "desc",
                    "page": "3",
                    "per_page": "50",
                    "data_view": "grid",
                    "layout_type": "sidebar",
                    "include_deleted": "true",
                }
            )
        )
        assert state.search == "bob"
        assert state.sort_by == "name"
        assert state.sort_order == "desc"
        assert state.page == 3
        assert state.per_page == 50
        assert state.view == "grid"
        assert state.layout == "sidebar"
        assert state.include_deleted is True

    def test_invalid_page_falls_back(self) -> None:
        state = TableState.from_request(_Req({"page": "abc", "per_page": "xyz"}))
        assert state.page == 1
        assert state.per_page == 20

    def test_negative_page_clamped(self) -> None:
        state = TableState.from_request(_Req({"page": "-2"}))
        assert state.page == 1

    def test_limit_alias(self) -> None:
        state = TableState.from_request(_Req({"per_page": "bad", "limit": "35"}))
        assert state.per_page == 35

    def test_invalid_view_falls_back(self) -> None:
        state = TableState.from_request(_Req({"data_view": "bogus"}))
        assert state.view == "tabular"

    def test_invalid_layout_falls_back(self) -> None:
        state = TableState.from_request(_Req({"layout_type": "bogus"}))
        assert state.layout == "stack"

    def test_defaults_validation_layout(self) -> None:
        state = TableState.from_request(_Req({}), defaults={"layout": 42})
        assert state.layout == "stack"

    def test_defaults_validation_view(self) -> None:
        state = TableState.from_request(_Req({}), defaults={"view": 42})
        assert state.view == "tabular"

    def test_defaults_unknown_view(self) -> None:
        state = TableState.from_request(_Req({}), defaults={"view": "bogus"})
        assert state.view == "tabular"

    def test_defaults_unknown_layout(self) -> None:
        state = TableState.from_request(_Req({}), defaults={"layout": "bogus"})
        assert state.layout == "stack"

    def test_invalid_sort_order_uses_default(self) -> None:
        state = TableState.from_request(_Req({"sort_order": "sideways"}))
        assert state.sort_order == "asc"

    def test_non_string_sort_by_ignored(self) -> None:
        state = TableState.from_request(_Req({}), defaults={"sort_by": 5})
        assert state.sort_by is None

    def test_filters_scalar(self) -> None:
        state = TableState.from_request(_Req({"filter_status": "active"}))
        assert state.filters == {"status": "active"}

    def test_filters_coercion(self) -> None:
        state = TableState.from_request(
            _Req(
                {
                    "filter_enabled": "true",
                    "filter_count": "7",
                    "filter_ratio": "1.5",
                    "filter_tag": "x",
                }
            )
        )
        assert state.filters == {
            "enabled": True,
            "count": 7,
            "ratio": 1.5,
            "tag": "x",
        }

    def test_filters_multivalue_list(self) -> None:
        state = TableState.from_request(
            _Req({"filter_status": ["a", "b", "a", ""]})
        )
        assert state.filters == {"status": ["a", "b"]}

    def test_filters_repaired_list_string(self) -> None:
        state = TableState.from_request(_Req({"filter_ids": '["1","2"]'}))
        assert state.filters == {"ids": [1, 2]}

    def test_known_keys_not_filters(self) -> None:
        state = TableState.from_request(_Req({"page": "2", "search": "x"}))
        assert state.filters == {}


class TestQueryParams:
    def test_to_query_params_only_non_defaults(self) -> None:
        state = TableState.from_request(_Req({}))
        assert state.to_query_params() == {}

    def test_to_query_params_overrides(self) -> None:
        state = TableState.from_request(
            _Req({"search": "x", "page": "2", "col_order": "a,b", "group_by": "g"})
        )
        params = state.to_query_params()
        assert params["search"] == "x"
        assert params["page"] == 2
        assert params["col_order"] == "a,b"
        assert params["group_by"] == "g"

    def test_to_query_params_filters_prefixed(self) -> None:
        state = TableState.from_request(_Req({"filter_status": "active"}))
        params = state.to_query_params()
        assert params["filter_status"] == "active"

    def test_to_query_params_collapsed_and_conflict(self) -> None:
        state = TableState.from_request(
            _Req({"collapsed_groups": "a,b", "include_deleted": "true"})
        )
        params = state.to_query_params()
        assert params["collapsed_groups"] == "a,b"
        assert params["include_deleted"] is True

    def test_to_query_params_exclude(self) -> None:
        state = TableState.from_request(_Req({"search": "x"}))
        assert state.to_query_params(exclude=["search"]) == {}

    def test_to_query_params_columns_order_key(self) -> None:
        state = TableState.from_request(_Req({"col_order": "a,b"}))
        params = state.to_query_params()
        assert params["col_order"] == "a,b"

    def test_to_url(self) -> None:
        state = TableState.from_request(_Req({"search": "x"}))
        assert state.to_url("/admin/users") == "/admin/users?search=x"

    def test_to_url_no_params(self) -> None:
        assert TableState.from_request(_Req({})).to_url() == ""


class TestCopies:
    def test_with_page(self) -> None:
        state = TableState.from_request(_Req({}))
        new = state.with_page(4)
        assert new.page == 4
        assert state.page == 1

    def test_with_per_page(self) -> None:
        state = TableState.from_request(_Req({"page": "3"}))
        new = state.with_per_page(50)
        assert new.per_page == 50
        assert new.page == 1

    def test_with_search_and_filter(self) -> None:
        state = TableState.from_request(_Req({}))
        s1 = state.with_search("q")
        s2 = s1.with_filter("status", "active")
        assert s2.search == "q"
        assert s2.filters == {"status": "active"}
        s3 = s2.without_filter("status")
        assert s3.filters == {}

    def test_with_sort_toggle(self) -> None:
        state = TableState.from_request(_Req({}))
        s1 = state.with_sort("name")
        assert s1.sort_order == "asc"
        s2 = s1.with_sort("name")
        assert s2.sort_order == "desc"
        s3 = s2.with_sort("other")
        assert s3.sort_by == "other"
        assert s3.sort_order == "asc"

    def test_with_view_layout_group(self) -> None:
        state = TableState.from_request(_Req({}))
        s1 = state.with_view("grid").with_layout("sidebar").with_group_by("cat")
        assert s1.view == "grid"
        assert s1.layout == "sidebar"
        assert s1.group_by == "cat"

    def test_clear_filters_and_sort(self) -> None:
        state = TableState.from_request(_Req({"search": "x", "sort_by": "name"}))
        cleared = state.clear_filters()
        assert cleared.search == ""
        assert cleared.filters == {}
        no_sort = cleared.clear_sort()
        assert no_sort.sort_by is None
        assert no_sort.sort_order == "asc"

    def test_with_include_deleted(self) -> None:
        state = TableState.from_request(_Req({}))
        assert state.with_include_deleted(True).include_deleted is True

    def test_model_copy_preserves_defaults(self) -> None:
        state = TableState.from_request(_Req({}), defaults={"view": "grid"})
        copy = state.model_copy()
        assert getattr(copy, "_defaults", None) == {"view": "grid"}


class TestResourcePrefixAndInputs:
    def test_resource_prefix(self) -> None:
        state = TableState.from_request(_Req({}))
        state.set_resource_prefix("users")
        assert state.get_resource_prefix() == "users"

    def test_render_hidden_inputs(self) -> None:
        state = TableState.from_request(_Req({"search": "x", "filter_tag": ["a", "b"]}))
        inputs = state.render_hidden_inputs()
        rendered = "".join("".join(el.iter_chunks()) for el in inputs)
        assert 'name="search"' in rendered
        assert 'value="x"' in rendered
        assert rendered.count('name="filter_tag"') == 2
        assert 'value="a"' in rendered
        assert 'value="b"' in rendered
        assert 'data-state="true"' in rendered

    def test_render_hidden_inputs_exclude(self) -> None:
        state = TableState.from_request(_Req({"search": "x"}))
        inputs = state.render_hidden_inputs(exclude=["search"])
        assert inputs == []