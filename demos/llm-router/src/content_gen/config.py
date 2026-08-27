"""Demo-specific configuration models.

Convention followed: **Config model** — ``ContentGenConfig`` extends
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
class ContentGenConfig(BaseConfig):
    """Root configuration for the llm-router demo.

    Maps 1:1 to the ``content_gen:`` section in ``application.yaml``.
    The framework merges YAML values + ``LEX_CONTENT_GEN__*`` env overrides
    into this model at boot time.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str | None] = "content_gen"
    name: str = "content_gen"
    enabled: bool = True

    default_style: str = Field(
        default="professional",
        description="Default writing style for content generation (professional | casual | technical)",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts on LLM failure",
    )

    # Uncomment to add more config fields:
    # model_name: str = Field(
    #     default="llama3",
    #     description="Model name for real LLM clients",
    # )
    # temperature: float = Field(
    #     default=0.7,
    #     description="Sampling temperature (0.0 = deterministic, 1.0 = creative)",
    # )
    # max_tokens: int = Field(
    #     default=1024,
    #     description="Maximum tokens in LLM response",
    # )
    # timeout: int = Field(
    #     default=30,
    #     description="Request timeout in seconds",
    # )


__all__ = ["ContentGenConfig"]
