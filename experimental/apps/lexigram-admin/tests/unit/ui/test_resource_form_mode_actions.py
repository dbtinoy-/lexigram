"""Create/edit table actions must target the resource's form mode."""

from __future__ import annotations

from lexigram.admin.actions.standard import CreateAction, EditAction
from lexigram.admin.resources.config import TableConfiguration
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.ui import TableState, render_to_string


def _html(mode: str) -> str:
    table = DataTable(
        data=[{"id": "1", "name": "Ada"}],
        state=TableState(),
        config=TableConfiguration(
            columns=[],
            actions=[EditAction()],
            header_actions=[CreateAction()],
            resource_name="people",
            resource_prefix="/admin/people",
            form_display_mode=mode,
        ),
    )
    return render_to_string(table)


def test_modal_mode_targets_modal_zone_for_create_and_edit() -> None:
    html = _html("modal")

    assert html.count('hx-target="#modal-container"') == 2
    assert "/admin/people/create" in html
    assert "/admin/people/1/edit" in html


def test_slider_mode_targets_slide_over_zone_for_create_and_edit() -> None:
    html = _html("slider")

    assert html.count('hx-target="#slide-over-container"') >= 2


def test_page_mode_uses_normal_links_for_create_and_edit() -> None:
    html = _html("page")

    assert 'href="/admin/people/create"' in html
    assert 'href="/admin/people/1/edit"' in html
    assert 'hx-get="/admin/people/create"' not in html
    assert 'hx-get="/admin/people/1/edit"' not in html
