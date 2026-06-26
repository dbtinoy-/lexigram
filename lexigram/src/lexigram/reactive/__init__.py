"""Lexigram Reactive — native stream composition for async apps.

Example:
    ```python
    from lexigram.reactive import Stream, ops

    async def gen():
        yield 1
        yield 2

    async def main():
        stream = Stream(gen())
        async for item in stream.pipe(ops.map(lambda x: x * 2)):
            print(item)
    ```
"""

from __future__ import annotations

from lexigram.reactive import operators as ops
from lexigram.reactive.core import EventStream, Op, Stream
from lexigram.reactive.exceptions import BackpressureError, ReactiveError
from lexigram.reactive.subjects import Subject, share

__all__ = [
    "BackpressureError",
    "EventStream",
    "Op",
    "ReactiveError",
    "Stream",
    "Subject",
    "ops",
    "share",
]
