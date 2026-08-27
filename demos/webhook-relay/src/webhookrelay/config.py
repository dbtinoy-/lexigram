"""Demo-specific configuration models.

Convention followed: **Config model** — ``WebhookRelayConfig`` extends
``BaseConfig`` (stdlib dataclass, NOT pydantic).  Each field uses
``Field()`` with a description and default value.  The framework
validates the YAML section against this model at boot time.

For full reference see:
- ``lexigram.config.BaseConfig`` — base config class
- ``lexigram.validation.Field`` — field descriptor with validation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class WebhookRelayConfig(BaseConfig):
    """Root configuration for the webhook-relay demo.

    Maps 1:1 to the ``webhookrelay:`` section in ``application.yaml``.
    The framework merges YAML values + ``LEX_WEBHOOKRELAY__*`` env overrides
    into this model at boot time.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str] = "webhookrelay"
    name: str = "webhookrelay"
    enabled: bool = True

    secret_key: str = Field(
        default="demo-secret-key",
        description="HMAC signing secret",
    )
    signature_header: str = Field(
        default="X-Hub-Signature-256",
        description="Signature header name",
    )
    max_payload_size: int = Field(
        default=1048576,
        description="Max payload size in bytes (1 MiB)",
    )
    retry_count: int = Field(
        default=3,
        description="Number of retry attempts",
    )

    # Uncomment to add more config fields:
    # event_timeout: int = Field(
    #     default=30,
    #     description="Event processing timeout in seconds",
    # )
    # log_events: bool = Field(
    #     default=True,
    #     description="Log all events",
    # )
    # allowed_sources: list[str] = Field(
    #     default_factory=lambda: ["shopify", "github", "stripe"],
    #     description="Allowed webhook sources",
    # )


__all__ = ["WebhookRelayConfig"]
