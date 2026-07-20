"""Reactive stream operators."""

# Operators deliberately re-export builtin-named functions (RxPY convention).
# ruff: noqa: A004

from __future__ import annotations

from lexigram.reactive.operators.control import catch, merge, skip, take
from lexigram.reactive.operators.time_ops import buffer, debounce, throttle, window
from lexigram.reactive.operators.transform import (
    distinct,
    filter,
    map,
    scan,
)

__all__ = [
    "buffer",
    "catch",
    "debounce",
    "distinct",
    "filter",
    "map",
    "merge",
    "scan",
    "skip",
    "take",
    "throttle",
    "window",
]
