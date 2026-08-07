"""Ambient identifier generation for the event-driven orders demo."""

from __future__ import annotations

from lexigram.identity import ambient as identity


def new_order_id() -> str:
    """Return a fresh order identifier."""
    return identity.generate_for("order")


__all__ = ["new_order_id"]
