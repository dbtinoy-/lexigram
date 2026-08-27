"""Demo-specific configuration models.

Convention followed: **Config model** — ``MonitorStackConfig`` extends
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
class MonitorStackConfig(BaseConfig):
    """Root configuration for the monitor-stack demo.

    Maps 1:1 to the ``monitorstack:`` section in ``application.yaml``.
    The framework merges YAML values + ``LEX_MONITORSTACK__*`` env overrides
    into this model at boot time.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str] = "monitorstack"
    name: str = "monitorstack"
    enabled: bool = True

    service_name: str = Field(
        default="demo-service",
        description="Service name for metrics tagging",
    )
    health_check_interval: int = Field(
        default=30,
        description="Seconds between health checks",
    )
    metrics_enabled: bool = Field(
        default=True,
        description="Enable metrics collection",
    )

    # Uncomment to add more config fields:
    # tracing_enabled: bool = Field(
    #     default=True,
    #     description="Enable request tracing",
    # )
    # log_level: str = Field(
    #     default="info",
    #     description="Log level for monitoring",
    # )
    # export_interval: int = Field(
    #     default=60,
    #     description="Seconds between metric exports",
    # )


__all__ = ["MonitorStackConfig"]
