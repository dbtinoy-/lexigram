"""Shared SVG rendering helpers for static chart components."""

from __future__ import annotations

from lexigram.ui.charts.types import ChartConfig, ChartDataPoint


def _parse_height(height: str, default: int) -> int:
    if height.endswith("px"):
        return int(height[:-2])
    return default


def _series_summary(data: list[ChartDataPoint]) -> str:
    return ", ".join(f"{d.label}: {d.value:g}" for d in data)


def _scheme_color(config: ChartConfig, fallback: str) -> str:
    if config.color_scheme == "auto":
        return fallback
    return config.color_scheme


def _point_color(point: ChartDataPoint, config: ChartConfig) -> str:
    if config.color_scheme != "auto" and point.color == "blue":
        return config.color_scheme
    return point.color
