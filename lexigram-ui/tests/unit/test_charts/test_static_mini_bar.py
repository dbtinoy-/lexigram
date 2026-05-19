from __future__ import annotations

from lexigram.ui.charts.static import MiniBar


class TestMiniBar:
    def test_zero_value_renders_zero_width_bar(self) -> None:
        bar = MiniBar(0)
        html = str(bar.render())
        assert "width:0.0%" in html
        assert "bg-muted" in html

    def test_positive_value_has_minimum_visible_width(self) -> None:
        bar = MiniBar(1, max_value=1000)
        html = str(bar.render())
        assert "width:2.0%" in html

    def test_full_value(self) -> None:
        bar = MiniBar(100)
        html = str(bar.render())
        assert "width:100.0%" in html

    def test_has_accessible_name(self) -> None:
        bar = MiniBar(42)
        html = str(bar.render())
        assert 'role="img"' in html
        assert 'aria-label="42 of 100"' in html

    def test_tooltip_reachable_by_keyboard(self) -> None:
        bar = MiniBar(42)
        html = str(bar.render())
        assert "group-focus-within:opacity-100" in html

    def test_negative_value_clamps_to_zero(self) -> None:
        bar = MiniBar(-5)
        html = str(bar.render())
        assert "width:0.0%" in html
        assert "bg-muted" in html