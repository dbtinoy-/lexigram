"""Shared test fixtures for lexigram-webhook."""

from __future__ import annotations

import sys
from pathlib import Path


import pytest

from lexigram.webhook.config import WebhookConfig
from lexigram.webhook.store.memory import InMemoryWebhookStore


@pytest.fixture
def config() -> WebhookConfig:
    """Default webhook configuration fixture."""
    return WebhookConfig()


@pytest.fixture
def store() -> InMemoryWebhookStore:
    """Fresh in-memory store fixture."""
    return InMemoryWebhookStore()


@pytest.fixture(autouse=True)
def _fake_public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve every hostname to a public IP so tests never hit live DNS."""
    import ipaddress

    from lexigram.contracts.security import url_safety as contracts_url_safety

    monkeypatch.setattr(
        contracts_url_safety,
        "resolve_hostname",
        lambda _: [ipaddress.ip_address("93.184.216.34")],
    )
