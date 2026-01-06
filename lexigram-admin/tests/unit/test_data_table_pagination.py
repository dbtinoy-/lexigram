from lexigram.admin.ui.columns.types import TextColumn
from lexigram.admin.ui.organisms.data_table import DataTable


def test_pagination_does_not_duplicate():
    cols = [TextColumn("id"), TextColumn("name")]
    # initial data for page 1
    data = list(map(lambda i: {"id": i, "name": f"name{i}"}, range(1, 11)))

    dt = DataTable(columns=cols, data=data, total=100, resource_prefix="/admin/posts")

    html1 = dt.render()
    assert html1.count('id="table-pagination"') == 1

    # Simulate moving to next page / filter change and re-render
    dt.state.page = 2
    dt.data = list(map(lambda i: {"id": i, "name": f"name{i}"}, range(11, 21)))
    html2 = dt.render()
    assert html2.count('id="table-pagination"') == 1

    # Simulate a sort/filter change
    dt.state.sort_by = "name"
    html3 = dt.render()
    assert html3.count('id="table-pagination"') == 1
