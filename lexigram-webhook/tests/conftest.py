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
