from lexigram.admin.ui.state import TableState


def test_to_url_contains_query_params():
    s = TableState(search="abc", page=2, per_page=25, view="grid")
    url = s.to_url(base_path="/admin/users")
    assert "/admin/users?" in url
    assert "search=abc" in url
    assert "page=2" in url
    assert "per_page=25" in url
    assert "data_view=grid" in url
