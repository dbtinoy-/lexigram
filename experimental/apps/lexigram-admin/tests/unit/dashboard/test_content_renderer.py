"""Tests for the host-side WidgetContent renderer."""

from __future__ import annotations

import pytest

from lexigram.admin.dashboard.content_renderer import render_content
from lexigram.contracts.admin.health_payload import HealthCheckPayload
from lexigram.contracts.admin.widget_content import (
    ChartContent,
    ChartPoint,
    EmptyContent,
    MessageContent,
    Stat,
    StatContent,
    TableCell,
    TableContent,
    Tone,
)
from lexigram.contracts.core.health import HealthStatus


def test_render_content_message_includes_text_and_tone_class() -> None:
    html = render_content(MessageContent(text="All good", tone=Tone.SUCCESS))
    assert "All good" in html
    assert "text-success" in html or "success" in html


def test_render_content_stat_content_lists_all_stats() -> None:
    html = render_content(
        StatContent(
            stats=(
                Stat(label="Requests", value="1,204", tone=Tone.DEFAULT),
                Stat(
                    label="Error rate",
                    value="2.1%",
                    tone=Tone.DANGER,
                    delta="-0.3%",
                ),
            )
        )
    )
    assert "Requests" in html
    assert "1,204" in html
    assert "Error rate" in html
    assert "2.1%" in html
    assert "-0.3%" in html
    assert "text-destructive" in html


def test_render_content_table_content_includes_columns_and_per_cell_tone() -> None:
    html = render_content(
        TableContent(
            columns=("Channel", "Status"),
            rows=(
                (
                    TableCell(text="Slack", tone=Tone.DEFAULT),
                    TableCell(text="healthy", tone=Tone.SUCCESS),
                ),
                (
                    TableCell(text="Email", tone=Tone.DEFAULT),
                    TableCell(text="stale", tone=Tone.WARNING),
                ),
            ),
        )
    )
    assert "Channel" in html
    assert "Status" in html
    assert "Slack" in html
    assert "Email" in html
    assert "healthy" in html
    assert "stale" in html
    assert "text-success" in html
    assert "text-warning" in html


def test_render_content_table_matches_tabular_table_visuals() -> None:
    html = render_content(
        TableContent(
            columns=("Channel", "Status"),
            rows=(
                (
                    TableCell(text="Slack", tone=Tone.DEFAULT),
                    TableCell(text="healthy", tone=Tone.SUCCESS),
                ),
                (
                    TableCell(text="Email", tone=Tone.DEFAULT),
                    TableCell(text="stale", tone=Tone.WARNING),
                ),
                (
                    TableCell(text="SMS", tone=Tone.DEFAULT),
                    TableCell(text="down", tone=Tone.DANGER),
                ),
            ),
        )
    )
    assert "min-w-full divide-y divide-border" in html
    assert "border-separate border-spacing-0" in html
    assert "bg-muted dark:bg-card-50 border-b border-border" in html
    assert "hover:bg-muted" in html
    assert "sticky top-0 z-20" in html
    assert "overflow-x-auto overflow-y-auto shadow-sm ring-1 ring-border" in html
    assert "bg-muted-30" in html
    assert html.count("bg-muted-30") == 1
    assert "transition-shadow" in html


@pytest.mark.parametrize("status", list(HealthStatus))
def test_render_content_health_payload_renders_each_health_status(
    status: HealthStatus,
) -> None:
    html = render_content(
        HealthCheckPayload(status=status, component="Billing", detail="available")
    )
    assert status.value in html
    assert "health-check-badge" in html


def test_render_content_empty_content_renders_empty_state() -> None:
    html = render_content(EmptyContent(title="Nothing here", message="No data yet."))
    assert "Nothing here" in html
    assert "No data yet." in html


def test_render_content_chart_content_renders_points() -> None:
    html = render_content(
        ChartContent(
            points=(
                ChartPoint(label="mon", value=10),
                ChartPoint(label="tue", value=20, tone=Tone.SUCCESS),
            )
        )
    )
    assert "mon" in html
    assert "tue" in html
    assert "10" in html
    assert "20" in html


def test_render_content_raises_type_error_for_unrecognized_type() -> None:
    with pytest.raises(TypeError):
        render_content(object())


PAYLOAD = '<img src=x onerror="alert(1)">'


def test_render_content_message_escapes_text() -> None:
    html = render_content(MessageContent(text=PAYLOAD, tone=Tone.DEFAULT))
    assert "<img" not in html
    assert '&lt;img src=x onerror="alert(1)"&gt;' in html


def test_render_content_stat_escapes_label_value_and_delta() -> None:
    html = render_content(
        StatContent(stats=(Stat(label=PAYLOAD, value=PAYLOAD, delta=PAYLOAD),))
    )
    assert "<img" not in html
    assert html.count("&lt;img") == 3


def test_render_content_table_escapes_headings_and_cells() -> None:
    html = render_content(
        TableContent(
            columns=(PAYLOAD,),
            rows=((TableCell(text=PAYLOAD, tone=Tone.DEFAULT),),),
        )
    )
    assert "<img" not in html
    assert html.count("&lt;img") == 2


def test_render_content_health_escapes_detail() -> None:
    html = render_content(
        HealthCheckPayload(
            status=HealthStatus.HEALTHY, component="Billing", detail=PAYLOAD
        )
    )
    assert "<img" not in html
    assert "&lt;img" in html


def test_render_content_chart_escapes_point_labels() -> None:
    html = render_content(ChartContent(points=(ChartPoint(label=PAYLOAD, value=10),)))
    assert "<img" not in html
    assert "&lt;img" in html


def test_render_content_empty_content_escapes_title_and_message() -> None:
    html = render_content(EmptyContent(title=PAYLOAD, message=PAYLOAD))
    assert "<img" not in html
    assert html.count("&lt;img") == 2
