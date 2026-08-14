from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class ChartType(StrEnum):
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    AREA = "area"
    SPARKLINE = "sparkline"
    MINI_BAR = "mini_bar"


@dataclass
class ChartDataPoint:
    label: str
    value: float
    color: str = "blue"
    secondary_value: float | None = None


@dataclass
class ChartConfig:
    title: str = ""
    height: str = "200px"
    show_grid: bool = True
    show_labels: bool = True
    animate: bool = True
    color_scheme: Literal["auto", "blue", "green", "red", "purple", "amber"] = "auto"
