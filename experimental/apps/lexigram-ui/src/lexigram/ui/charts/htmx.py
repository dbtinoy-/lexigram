from __future__ import annotations

from typing import Any


def hx_chart_attrs(
    endpoint: str,
    *,
    refresh_interval: int | None = None,
    target: str | None = None,
    swap: str = "innerHTML",
) -> dict[str, Any]:
    triggers = ["load"]
    if refresh_interval and refresh_interval > 0:
        triggers.append(f"every {refresh_interval * 1000}ms")

    attrs: dict[str, Any] = {
        "hx-get": endpoint,
        "hx-trigger": ", ".join(triggers),
        "hx-swap": swap,
    }
    if target:
        attrs["hx-target"] = target
    return attrs


def chart_skeleton() -> dict[str, Any]:
    return {
        "class": "animate-pulse space-y-2 p-4",
    }
