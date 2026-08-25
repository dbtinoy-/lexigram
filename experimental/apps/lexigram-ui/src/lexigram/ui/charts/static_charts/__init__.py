"""Static SVG chart components."""

from __future__ import annotations

from lexigram.ui.charts.static_charts.bar import BarChart as BarChart
from lexigram.ui.charts.static_charts.line import (
    AreaChart as AreaChart,
)
from lexigram.ui.charts.static_charts.line import (
    LineChart as LineChart,
)
from lexigram.ui.charts.static_charts.pie import PieChart as PieChart
from lexigram.ui.charts.static_charts.sparkline import (
    MiniBar as MiniBar,
)
from lexigram.ui.charts.static_charts.sparkline import (
    Sparkline as Sparkline,
)

__all__ = [
    "AreaChart",
    "BarChart",
    "LineChart",
    "MiniBar",
    "PieChart",
    "Sparkline",
]
