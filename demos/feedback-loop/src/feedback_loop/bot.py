"""Canned Q→A registry with fixed trace ids (two deliberately poor answers)."""

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
