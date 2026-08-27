"""Canned Q→A registry with fixed trace ids (two deliberately poor answers).

Convention: domain data lives in the repository layer.  The ``BOT`` dict
maps question keys to canned answers; ``TRACE_IDS`` provides stable
trace identifiers for each question; ``POOR_KEYS`` marks the two
deliberately poor answers that drive the regression flow.

The canned questions in ``BOT`` (and their trace ids) are *domain data*,
not CLI or UI concerns — they stay here regardless of how the demo is
invoked.
"""

from __future__ import annotations

BOT: dict[str, str] = {
    "refund-policy": "Contact support and maybe you get money back sometime.",
    "shipping-time": "It arrives when it arrives.",
    "track-order": "Use the tracking id in your shipment email to follow your parcel.",
    "warranty": "Every product includes a 24 month limited warranty covering manufacturing defects.",
}

TRACE_IDS: dict[str, str] = {
    key: f"t{index + 1}" for index, key in enumerate(sorted(BOT))
}

POOR_KEYS: set[str] = {"refund-policy", "shipping-time"}
