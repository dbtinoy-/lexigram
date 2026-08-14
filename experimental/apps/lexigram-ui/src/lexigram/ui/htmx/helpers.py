"""HTMX performance optimization patterns and helpers.

This module provides utilities for optimizing HTMX-based interactions with
techniques like selective swaps, prefetching, and efficient DOM updates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htpy import Element


def hx_swap_oob(*elements: tuple[str, Element]) -> list[Element]:
    """Create out-of-band swap elements for multiple updates.

    Out-of-band (OOB) swaps allow updating multiple parts of the page
    with a single HTMX request, improving performance.

    Args:
        *elements: Tuples of (target_id, element) to swap

    Returns:
        List of elements with hx-swap-oob attributes

    Example:
        ```python
        from htpy import div

        # Update multiple elements at once
        return [
            div["Main content"],  # Normal swap
            *hx_swap_oob(
                ("notifications", Badge("3 new messages")),
                ("user-menu", UserMenu(user)),
            )
        ]
        ```
    """
    from htpy import div

    result = []
    for target_id, element in elements:
        # Wrap in div with hx-swap-oob attribute
        wrapped = div[element][{"hx-swap-oob": f"innerHTML:#{target_id}"}]
        result.append(wrapped)
    return result


def hx_prefetch(
    url: str,
    trigger: str = "mouseenter",
    threshold: str = "200ms",
) -> dict[str, str]:
    """Create attributes for HTMX prefetching.

    Prefetch content before the user clicks, making navigation instant.

    Args:
        url: URL to prefetch
        trigger: Event that triggers prefetch (default: mouseenter)
        threshold: Delay before prefetching (default: 200ms)

    Returns:
        Dictionary of HTMX attributes

    Example:
        ```python
        # Prefetch on hover
        a["View Details"][
            {
                "href": "/users/123",
                **hx_prefetch("/users/123"),
            }
        ]
        ```
    """
    return {
        "hx-get": url,
        "hx-trigger": f"{trigger} throttle:{threshold}",
        "hx-swap": "none",  # Don't swap on prefetch
    }


def hx_lazy_load(
    url: str,
    trigger: str = "revealed",
    threshold: str = "0px",
    placeholder: str | None = None,
) -> dict[str, str]:
    """Create attributes for lazy loading content when scrolled into view.

    Args:
        url: URL to load content from
        trigger: Trigger event (default: revealed)
        threshold: Distance from viewport to trigger (default: 0px)
        placeholder: Placeholder text while loading

    Returns:
        Dictionary of HTMX attributes

    Example:
        ```python
        # Load when scrolled into view
        div["Loading..."][
            {
                **hx_lazy_load("/api/heavy-content"),
            }
        ]
        ```
    """
    attrs = {
        "hx-get": url,
        "hx-trigger": f"{trigger} threshold:{threshold}",
        "hx-swap": "outerHTML",
    }
    if placeholder:
        attrs["hx-indicator"] = placeholder
    return attrs


def hx_morph(target: str | None = None) -> dict[str, str]:
    """Create attributes for morphing (minimal DOM updates).

    Morphing intelligently updates only changed parts of the DOM,
    preserving focus, scroll position, and component state.

    Args:
        target: Optional target selector

    Returns:
        Dictionary of HTMX attributes

    Example:
        ```python
        # Morph instead of replacing entire element
        div["Content"][
            {
                **hx_morph(),
                "hx-get": "/api/update",
            }
        ]
        ```
    """
    attrs = {"hx-swap": "morph"}
    if target:
        attrs["hx-target"] = target
    return attrs


def hx_preserve(*selectors: str) -> dict[str, str]:
    """Create attributes to preserve elements during swap.

    Useful for maintaining state of inputs, scroll position, etc.

    Args:
        *selectors: CSS selectors of elements to preserve

    Returns:
        Dictionary of HTMX attributes

    Example:
        ```python
        # Preserve input values during update
        form["..."][
            {
                **hx_preserve("input", "textarea"),
            }
        ]
        ```
    """
    return {"hx-preserve": ",".join(selectors)}


def hx_boost(
    enable: bool = True,
    target: str | None = None,
    swap: str = "innerHTML",
) -> dict[str, str]:
    """Create attributes for boosting standard links/forms.

    Boosting converts normal links and forms to use HTMX, making
    the site feel like a SPA without rewriting existing code.

    Args:
        enable: Whether to enable boosting
        target: Target selector for swaps
        swap: Swap strategy

    Returns:
        Dictionary of HTMX attributes

    Example:
        ```python
        # Boost all links in navigation
        nav["..."][
            {
                **hx_boost(target="#content"),
            }
        ]
        ```
    """
    attrs = {"hx-boost": "true" if enable else "false"}
    if target:
        attrs["hx-target"] = target
    if swap != "innerHTML":
        attrs["hx-swap"] = swap
    return attrs


def hx_debounce(delay: str = "500ms") -> dict[str, str]:
    """Create attributes for debouncing requests.

    Debouncing prevents sending too many requests during rapid user input.

    Args:
        delay: Debounce delay (e.g., "500ms", "1s")

    Returns:
        Dictionary of HTMX attributes

    Example:
        ```python
        # Debounce search input
        input_[
            {
                "type": "search",
                "hx-get": "/search",
                "hx-trigger": "keyup changed",
                **hx_debounce("300ms"),
            }
        ]
        ```
    """
    return {"hx-trigger": f"keyup changed delay:{delay}"}


def hx_optimistic(
    indicator: str | None = None,
    settle_delay: str = "0ms",
) -> dict[str, str]:
    """Create attributes for optimistic UI updates.

    Shows immediate feedback while request is processing.

    Args:
        indicator: Loading indicator selector
        settle_delay: Delay before settling (default: 0ms for instant)

    Returns:
        Dictionary of HTMX attributes

    Example:
        ```python
        # Show immediate update, then settle
        button["Like"][
            {
                **hx_optimistic(indicator="#spinner"),
                "hx-post": "/like",
            }
        ]
        ```
    """
    attrs = {"hx-swap": f"innerHTML settle:{settle_delay}"}
    if indicator:
        attrs["hx-indicator"] = indicator
    return attrs


def hx_polling(
    interval: str = "2s",
    url: str | None = None,
) -> dict[str, str]:
    """Create attributes for polling updates.

    Args:
        interval: Polling interval (e.g., "2s", "5000ms")
        url: Optional URL to poll (uses current if not specified)

    Returns:
        Dictionary of HTMX attributes

    Example:
        ```python
        # Poll for updates every 5 seconds
        div["Status: ..."][
            {
                **hx_polling("5s", "/api/status"),
            }
        ]
        ```
    """
    attrs = {"hx-trigger": f"every {interval}"}
    if url:
        attrs["hx-get"] = url
    return attrs


def hx_websocket(url: str) -> dict[str, str]:
    """Create attributes for WebSocket connection.

    Args:
        url: WebSocket URL

    Returns:
        Dictionary of HTMX attributes

    Example:
        ```python
        # Connect to WebSocket
        div["Messages"][
            {
                **hx_websocket("ws://localhost:8000/ws"),
            }
        ]
        ```
    """
    return {"hx-ws": f"connect:{url}"}


def hx_sse(url: str, swap: str = "message") -> dict[str, str]:
    """Create attributes for Server-Sent Events.

    Args:
        url: SSE endpoint URL
        swap: Event name to swap on (default: message)

    Returns:
        Dictionary of HTMX attributes

    Example:
        ```python
        # Listen for SSE updates
        div["Live Updates"][
            {
                **hx_sse("/events", swap="update"),
            }
        ]
        ```
    """
    return {
        "hx-sse": f"connect:{url}",
        "hx-trigger": f"sse:{swap}",
    }


def optimistic_update(
    target: str,
    content: str,
    trigger: str = "click",
    **kwargs: Any,
) -> dict[str, Any]:
    """Optimistic UI update via hx-on::before-request.

    Args:
        target: CSS selector for the target element.
        content: HTML content to swap in immediately.
        trigger: HTMX trigger event. Defaults to "click".

    Returns:
        HTMX attributes dict for optimistic update.
    """
    return {
        "hx-on::before-request": f"document.querySelector('{target}').innerHTML = '{content}'",
        **kwargs,
    }


def hx_optimistic_swap(target: str, html_snippet: str) -> dict[str, Any]:
    """Optimistic swap on click via hx-on attribute.

    Note: this is distinct from `hx_optimistic` above, which produces a
    settle-delay indicator pattern. `hx_optimistic_swap` swaps content
    immediately into a target on click — useful for instant placeholders.

    Args:
        target: CSS selector for the target element.
        html_snippet: HTML content to swap in (single quotes escaped).

    Returns:
        HTMX attributes dict for optimistic swap.
    """
    safe_snippet = html_snippet.replace("'", "\\'")
    return {
        "hx-on-click": f"document.querySelector('{target}').innerHTML = '{safe_snippet}'",
    }
