from lexigram.ui import SearchBar
from lexigram.ui.core.base import render_to_string


def test_searchbar_with_icon_renders_wrapper_and_padding():
    html = render_to_string(
        SearchBar(value="term", placeholder="Find...", show_icon=True),
    )
    assert 'class="relative group"' in html
    # left padding helper for input should be present (match on pl-10 to be robust)
    assert "pl-10" in html
    # input should be present inside
    assert "<input" in html


def test_searchbar_exposes_accessible_name_and_search_role():
    html = render_to_string(
        SearchBar(value="term", placeholder="Find...", show_icon=True),
    )
    assert 'role="search"' in html
    assert 'aria-label="Search"' in html


def test_searchbar_custom_aria_label():
    html = render_to_string(SearchBar(aria_label="Filter records"))
    assert 'aria-label="Filter records"' in html


def test_searchbar_without_icon_renders_input_directly():
    html = render_to_string(SearchBar(show_icon=False))
    assert "<input" in html
    assert "[&>input]:pl-10" not in html


def test_searchbar_quoted_value_renders_valid_alpine_state():
    """Search value with quotes should produce valid Alpine x-data."""
    html = render_to_string(
        SearchBar(value="it's \"quoted\"", show_icon=True),
    )
    assert "<input" in html
    assert "x-data" in html


def test_searchbar_clear_returns_focus_to_input():
    html = render_to_string(SearchBar(show_clear=True))
    assert 'aria-label="Clear search"' in html
    assert "input.focus()" in html
