"""Convenience fragment helpers for live chart/stat widget bodies.

``render_chart_fragment`` and ``render_stat_fragment`` build a
``ChartContent``/``StatContent`` and delegate to the shared dispatcher, so
live endpoints and inline renders use identical tone/empty-state semantics.
"""

from __future__ import annotations

from lexigram.admin.dashboard.content_renderer import (
    render_chart_fragment,
    render_stat_fragment,
)
from lexigram.contracts.admin.widget_content import ChartPoint, Stat, Tone


class TestRenderChartFragment:
    def test_delegates_points_to_shared_dispatcher(self) -> None:
        html = render_chart_fragment(
            "bar",
            [
                ChartPoint(label="users", value=3),
                ChartPoint(label="roles", value=2),
            ],
        )
        assert "users" in html
        assert "roles" in html
        assert "No chart data" not in html

    def test_empty_points_render_empty_state(self) -> None:
        html = render_chart_fragment("bar", [])
        assert "No chart data" in html


class TestRenderStatFragment:
    def test_delegates_stats_to_shared_dispatcher(self) -> None:
        html = render_stat_fragment(
            [Stat(label="Resources", value="12", tone=Tone.PRIMARY)]
        )
        assert "Resources" in html
        assert "12" in html
        assert "text-primary" in html

    def test_delta_and_danger_tone_render(self) -> None:
        html = render_stat_fragment(
            [
                Stat(
                    label="Error rate",
                    value="2.1%",
                    delta="-0.3%",
                    tone=Tone.DANGER,
                )
            ]
        )
        assert "-0.3%" in html
        assert "text-destructive" in html
