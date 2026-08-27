"""Demo-specific configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class WebhookRelayConfig(BaseConfig):
    """Root configuration for the webhook-relay demo."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str | None] = "webhookrelay"

    secret_key: str = Field(default="demo-secret-key", description="HMAC signing secret")
    signature_header: str = Field(default="X-Hub-Signature-256", description="Signature header name")
    max_payload_size: int = Field(default=1048576, description="Max payload size in bytes")
    retry_count: int = Field(default=3, description="Number of retry attempts")


__all__ = ["WebhookRelayConfig"]
