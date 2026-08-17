"""HTMX helpers for Lexigram UI — consolidated re-exports."""

from __future__ import annotations

import sys as _sys

from lexigram.ui.htmx.action_response import HtmxActionResponse, ToastData, ToastType
from lexigram.ui.htmx.attrs import (
    hx_delete,
    hx_get,
    hx_headers,
    hx_patch,
    hx_post,
    hx_put,
    hx_swap,
    hx_target,
    hx_trigger,
    hx_vals,
)
from lexigram.ui.htmx.helpers import (
    hx_boost,
    hx_debounce,
    hx_lazy_load,
    hx_morph,
    hx_optimistic,
    hx_polling,
    hx_prefetch,
    hx_preserve,
    hx_sse,
    hx_swap_oob,
    hx_websocket,
)
from lexigram.ui.htmx.sse import SSE, SSEEventType, SSEMessage, SSEStream
from lexigram.ui.htmx.table_attrs import HTMXAttrs, HTMXAttrsBuilder

__all__ = [
    "HTMXAttrs",
    "HTMXAttrsBuilder",
    "HtmxActionResponse",
    "SSE",
    "SSEEventType",
    "SSEMessage",
    "SSEStream",
    "ToastData",
    "ToastType",
    "hx_boost",
    "hx_debounce",
    "hx_delete",
    "hx_get",
    "hx_headers",
    "hx_lazy_load",
    "hx_morph",
    "hx_optimistic",
    "hx_patch",
    "hx_polling",
    "hx_post",
    "hx_prefetch",
    "hx_preserve",
    "hx_put",
    "hx_sse",
    "hx_swap",
    "hx_swap_oob",
    "hx_target",
    "hx_trigger",
    "hx_vals",
    "hx_websocket",
]

# Expose the module as itself so public-API consumers can resolve `htmx`.
htmx = _sys.modules[__name__]
