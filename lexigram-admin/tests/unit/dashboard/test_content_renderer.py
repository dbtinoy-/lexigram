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
