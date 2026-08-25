"""Static SVG chart renderers.

The chart components live in the ``static_charts`` package (one module per
chart family, sharing ``_svg_helpers``); they are re-exported here so the
public import paths are unchanged.
"""

from __future__ import annotations

from lexigram.ui.charts.static_charts import (
    AreaChart as AreaChart,
)
from lexigram.ui.charts.static_charts import (
    BarChart as BarChart,
)
from lexigram.ui.charts.static_charts import (
    LineChart as LineChart,
)
from lexigram.ui.charts.static_charts import (
    MiniBar as MiniBar,
)
from lexigram.ui.charts.static_charts import (
    PieChart as PieChart,
)
from lexigram.ui.charts.static_charts import (
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
