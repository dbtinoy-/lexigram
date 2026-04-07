"""HTMX helpers for Lexigram Admin UI."""

from __future__ import annotations

from typing import Any


def hx_get(url: str, **kwargs: Any) -> dict[str, Any]:
    """HTMX GET request attribute."""
    return {"hx-get": url, **kwargs}


def hx_post(url: str, **kwargs: Any) -> dict[str, Any]:
    """HTMX POST request attribute."""
    return {"hx-post": url, **kwargs}


def hx_put(url: str, **kwargs: Any) -> dict[str, Any]:
    """HTMX PUT request attribute."""
    return {"hx-put": url, **kwargs}


def hx_delete(url: str, **kwargs: Any) -> dict[str, Any]:
    """HTMX DELETE request attribute."""
    return {"hx-delete": url, **kwargs}


def hx_patch(url: str, **kwargs: Any) -> dict[str, Any]:
    """HTMX PATCH request attribute."""
    return {"hx-patch": url, **kwargs}


def hx_target(target: str) -> dict[str, Any]:
    """HTMX target attribute."""
    return {"hx-target": target}


def hx_swap(swap: str) -> dict[str, Any]:
    """HTMX swap attribute."""
    return {"hx-swap": swap}


def hx_trigger(trigger: str) -> dict[str, Any]:
    """HTMX trigger attribute."""
    return {"hx-trigger": trigger}


def hx_vals(vals: dict[str, Any] | str) -> dict[str, Any]:
    """HTMX values attribute."""
    from lexigram.serialization import dumps_str

    if isinstance(vals, dict):
        vals = dumps_str(vals)
    return {"hx-vals": vals}


def hx_headers(headers: dict[str, Any] | str) -> dict[str, Any]:
    """HTMX headers attribute."""
    from lexigram.serialization import dumps_str

    if isinstance(headers, dict):
        headers = dumps_str(headers)
    return {"hx-headers": headers}
