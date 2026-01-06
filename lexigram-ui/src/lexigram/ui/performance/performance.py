"""
Performance utilities for Lexigram Admin UI.

Provides response optimization, render caching, and lazy loading
helpers for HTMX-powered components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import wraps
from hashlib import sha256
from time import time
from typing import TYPE_CHECKING, Any, TypeVar

from lexigram.logging import get_logger
from lexigram.serialization import dumps_str
from lexigram.ui.core.base import render_to_string
from lexigram.ui.core.zones import Zones

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

T = TypeVar("T")


# === Response Optimization ===


@dataclass
class ResponseOptimizer:
    """
    Optimize HTMX responses with caching and conditional rendering.

    Features:
    - ETag-based caching for unchanged content
    - Content hashing to detect changes
    - Conditional response headers
    """

    def compute_etag(self, content: str) -> str:
        """Compute ETag hash for content."""
        return sha256(content.encode()).hexdigest()[:16]

    def should_return_304(
        self,
        content: str,
        request_etag: str | None,
    ) -> bool:
        """Check if we can return 304 Not Modified."""
        if not request_etag:
            return False
        current_etag = self.compute_etag(content)
        return request_etag in (current_etag, f'"{current_etag}"')

    def optimize_response(
        self,
        content: str,
        request_etag: str | None = None,
    ) -> tuple[str, int, dict[str, str]]:
        """
        Optimize response with caching headers.

        Args:
            content: The HTML content to return
            request_etag: The If-None-Match header value from request

        Returns:
            Tuple of (content, status_code, headers)
        """
        etag = self.compute_etag(content)

        if self.should_return_304(content, request_etag):
            return "", 304, {"ETag": f'"{etag}"'}

        headers = {
            "ETag": f'"{etag}"',
            "Cache-Control": "private, no-cache",
            "Vary": "HX-Request",
        }

        return content, 200, headers


def optimize_htmx_response(
    content: str,
    request_etag: str | None = None,
    optimizer: ResponseOptimizer | None = None,
) -> tuple[str, int, dict[str, str]]:
    """Convenience function for response optimization.

    Args:
        content: HTML content to optimize.
        request_etag: ETag from the incoming request for cache validation.
        optimizer: ResponseOptimizer instance. When None, returns the content unchanged.
    """
    if optimizer is None:
        return content, 200, {}
    return optimizer.optimize_response(content, request_etag)


# === Render Caching ===


@dataclass
class RenderCache:
    """
    LRU cache for rendered component fragments.

    Use for expensive-to-render components that don't change often.
    """

    _cache: dict[str, tuple[str, float]] = field(default_factory=dict)
    max_size: int = 100
    ttl_seconds: float = 60.0

    def _make_key(self, component_name: str, **kwargs: Any) -> str:
        """Create cache key from component name and params."""
        sorted_items = sorted(kwargs.items())
        params_str = dumps_str(sorted_items, sort_keys=True, default=str)
        return f"{component_name}:{sha256(params_str.encode()).hexdigest()}"

    def get(self, component_name: str, **kwargs: Any) -> str | None:
        """Get cached render result if valid."""
        key = self._make_key(component_name, **kwargs)
        if key not in self._cache:
            logger.debug("render_cache.miss", component=component_name)
            return None

        content, cached_at = self._cache[key]
        if time() - cached_at > self.ttl_seconds:
            del self._cache[key]
            logger.debug("render_cache.expired", component=component_name)
            return None

        logger.debug("render_cache.hit", component=component_name)
        return content

    def set(self, component_name: str, content: str, **kwargs: Any) -> None:
        """Cache a render result."""
        # Evict old entries if at capacity
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
            logger.debug("render_cache.evicted", component=component_name)

        key = self._make_key(component_name, **kwargs)
        self._cache[key] = (content, time())
        logger.debug("render_cache.stored", component=component_name)

    def invalidate(self, component_name: str | None = None) -> None:
        """Invalidate cache entries."""
        if component_name is None:
            self._cache.clear()
        else:
            keys_to_remove = [
                k for k in self._cache if k.startswith(f"{component_name}:")
            ]
            for key in keys_to_remove:
                del self._cache[key]

    def cached(
        self,
        component_name: str | None = None,
    ) -> Callable[[Callable[..., str]], Callable[..., str]]:
        """Decorator for caching render methods."""

        def decorator(func: Callable[..., str]) -> Callable[..., str]:
            name = component_name or func.__qualname__

            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> str:
                # Try cache first
                cached = self.get(name, **kwargs)
                if cached is not None:
                    return cached

                # Render and cache
                result = func(*args, **kwargs)
                self.set(name, result, **kwargs)
                return result

            return wrapper

        return decorator


def cached_render(
    component_name: str | None = None,
    cache: RenderCache | None = None,
) -> Callable[[Callable[..., str]], Callable[..., str]]:
    """Decorator for caching component renders.

    Args:
        component_name: Name for the cached component fragment.
        cache: RenderCache instance to use. When None, returns an identity decorator.
    """
    if cache is None:
        return lambda func: func
    return cache.cached(component_name)


# === Lazy Loading ===


def lazy_load_placeholder(
    url: str,
    target_id: str,
    trigger: str = "load",
    placeholder: str | None = None,
) -> str:
    """
    Create a lazy-load placeholder that fetches content on trigger.

    Args:
        url: URL to fetch content from
        target_id: ID of the element to replace
        trigger: HTMX trigger (load, revealed, intersect, etc.)
        placeholder: Optional placeholder content (defaults to skeleton)

    Returns:
        HTML string for the placeholder
    """
    from lexigram.ui.atoms.skeleton import Skeleton
    from lexigram.ui.core.base import el

    if placeholder is None:
        placeholder = render_to_string(Skeleton(variant="table", rows=5))

    return render_to_string(
        el(
            "div",
            placeholder,
            id=target_id,
            hx_get=url,
            hx_trigger=trigger,
            hx_swap="outerHTML",
        ),
    )


def infinite_scroll_trigger(
    url: str,
    target: str | None = None,
    swap: str = "beforeend",
    threshold: str = "200px",
) -> str:
    """
    Create an infinite scroll trigger element.

    Args:
        url: URL to fetch next page from
        target: HTMX target selector (defaults to Zones.DATA)
        swap: HTMX swap mode
        threshold: Distance from bottom to trigger load

    Returns:
        HTML string for the trigger element
    """
    from lexigram.ui.atoms.spinner import Spinner
    from lexigram.ui.core.base import el

    target = target or Zones.DATA.selector

    return render_to_string(
        el(
            "div",
            Spinner(size="sm"),
            class_="flex justify-center py-4",
            hx_get=url,
            hx_trigger=f"revealed threshold:{threshold}",
            hx_target=target,
            hx_swap=swap,
        ),
    )


# === Debouncing ===


from lexigram.ui.config import DebounceConfig


def debounced_search_attrs(
    url: str,
    delay_ms: int = 300,
    target: str | None = None,
) -> dict[str, str]:
    """
    Generate HTMX attributes for a debounced search input.

    Args:
        url: URL to search endpoint
        delay_ms: Debounce delay in milliseconds
        target: HTMX target (defaults to Zones.DATA)

    Returns:
        Dictionary of HTMX attributes
    """
    target = target or Zones.DATA.selector
    config = DebounceConfig(delay_ms=delay_ms)

    return {
        "hx-get": url,
        "hx-trigger": config.to_trigger("input"),
        "hx-target": target,
        "hx-swap": Zones.DATA.swap_mode.value,
        "hx-indicator": ".htmx-indicator",
    }


# === Request Coalescing ===


@dataclass
class RequestCoalescer:
    """
    Coalesce rapid-fire requests into single requests.

    Useful for batch operations or rapid filter changes.
    """

    pending: dict[str, Any] = field(default_factory=dict)
    window_ms: float = 100

    def add(self, key: str, value: Any) -> None:
        """Add a value to coalesce."""
        self.pending[key] = value

    def flush(self) -> dict[str, Any]:
        """Get and clear all pending values."""
        result = dict(self.pending)
        self.pending.clear()
        return result


# === Performance Middleware Helpers ===


def add_htmx_timing_header(
    headers: dict[str, str],
    render_time_ms: float,
) -> dict[str, str]:
    """Add Server-Timing header for HTMX requests."""
    headers = dict(headers)
    headers["Server-Timing"] = f"render;dur={render_time_ms:.2f}"
    return headers


def measure_render_time(func: Callable[..., str]) -> Callable[..., tuple[str, float]]:
    """Decorator to measure render time."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> tuple[str, float]:
        start = time()
        result = func(*args, **kwargs)
        elapsed_ms = (time() - start) * 1000
        return result, elapsed_ms

    return wrapper
