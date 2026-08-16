"""Reactive layer exceptions."""

from __future__ import annotations

from lexigram.contracts.exceptions.base import LexigramError


class ReactiveError(LexigramError):
    """Base exception for the reactive stream layer."""


class BackpressureError(ReactiveError):
    """Raised when a subscriber channel overflows under a non-blocking policy."""
