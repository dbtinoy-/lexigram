from shorts_creator.ui.components.run_history import RunHistoryTable


def _run(rid="r1", duration=34.266667):
    return {
        "run_id": rid,
        "idea": "Test Idea",
        "status": "completed",
        "duration_s": duration,
        "output": "data/renders/x.mp4",
    }


def test_expanded_detail_formats_duration():
    html = RunHistoryTable([_run()], expandable=True)
    assert "34.3s" in html
    assert "34.266667" not in html


def test_expanded_detail_links_to_run():
    html = RunHistoryTable([_run()], expandable=True)
    assert 'href="/history/r1"' in html


def test_rows_are_accessible_without_inline_onclick():
    html = RunHistoryTable([_run()], expandable=True)
    assert 'data-expandable-row="true"' in html
    assert 'aria-expanded="false"' in html
    assert 'role="button"' in html
    assert "onclick=" not in html


def test_nonexpandable_table_has_no_row_attributes():
    html = RunHistoryTable([_run()], expandable=False)
    assert "data-expandable-row" not in html
    assert "onclick=" not in html


def test_project_column_links_to_project_when_projects_provided():
    run = _run()
    run["project_id"] = "p1"
    html = RunHistoryTable([run], expandable=True, projects={"p1": "My Project"})
    assert "Project" in html
    assert 'href="/projects/p1"' in html
    assert "My Project" in html


def test_project_column_shows_dash_without_projects_map():
    run = _run()
    run["project_id"] = "p1"
    html = RunHistoryTable([run], expandable=True)
    assert 'href="/projects/p1"' not in html


def test_detail_spacer_rows_span_seven_columns():
    html = RunHistoryTable([_run()], expandable=True)
    assert html.count('colspan="7"') == 2
