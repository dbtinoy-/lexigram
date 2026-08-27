"""Demo-specific configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class MonitorStackConfig(BaseConfig):
    """Root configuration for the monitor-stack demo."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str | None] = "monitorstack"

    service_name: str = Field(default="demo-service", description="Service name for metrics")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")


__all__ = ["MonitorStackConfig"]
