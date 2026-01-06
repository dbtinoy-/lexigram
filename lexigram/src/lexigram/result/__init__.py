"""Result pattern — concrete Ok/Err implementation and utility functions.

Canonical import path for all callers::

    from lexigram.result import Result, Ok, Err
    from lexigram.result import as_result, as_result_sync, collect, partition
    from lexigram.result import ResultPipeline, pipeline
    from lexigram.result import try_catch, try_catch_sync
"""

from __future__ import annotations

from lexigram.result._pipeline import ResultPipeline, pipeline
from lexigram.result.errors import ResultError, UnwrapError
from lexigram.result.types import Err, Ok, Result
from lexigram.result.utils import (
    as_result,
    as_result_sync,
    collect,
    partition,
    try_catch,
    try_catch_sync,
)

__all__ = [
    "Err",
    "Ok",
    "Result",
    "ResultError",
    "ResultPipeline",
    "UnwrapError",
    "as_result",
    "as_result_sync",
    "collect",
    "partition",
    "pipeline",
    "try_catch",
    "try_catch_sync",
]
