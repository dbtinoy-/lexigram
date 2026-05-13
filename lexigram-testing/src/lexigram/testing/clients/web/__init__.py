"""Test client for Lexigram Web applications."""

from __future__ import annotations

try:
    from lexigram.testing.clients.web.bed import WebTestBed, with_web
    from lexigram.testing.clients.web.client import TestResponse, WebTestClient
except ImportError:
    WebTestBed = None  # type: ignore[assignment,misc]
    WebTestClient = None  # type: ignore[assignment,misc]
    TestResponse = None  # type: ignore[assignment,misc]
    with_web = None  # type: ignore[assignment]

__all__ = ["TestResponse", "WebTestBed", "WebTestClient", "with_web"]
