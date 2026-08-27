"""Ratings-to-regression loop demo.

Convention: the top-level ``__init__.py`` re-exports public API so
consumers can write ``from feedback_loop import create_app``.
"""

from __future__ import annotations

from feedback_loop.app import build_modules, build_providers, create_app
from feedback_loop.errors import (
    InvalidRatingError,
    NoLowRatedError,
    UnknownQuestionError,
    UnknownTraceError,
)

__all__ = [
    "InvalidRatingError",
    "NoLowRatedError",
    "UnknownQuestionError",
    "UnknownTraceError",
    "build_modules",
    "build_providers",
    "create_app",
]
