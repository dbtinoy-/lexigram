"""Configuration models for the LLM reproducibility demo.

Two config sections:

1. ``SamplingConfig`` — temperature, top_p, max_tokens.
2. ``ExperimentConfig`` — root config aggregating sampling, model,
   seed, iterations, and recording switches.

The ``ExperimentProvider`` reads the ``experiment:`` section from
``application.yaml`` automatically via ``config_key`` / ``config_model``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, cast

import yaml

from lexigram.config import BaseConfig
from lexigram.validation import ConfigDict, Field

APP_YAML = Path(__file__).resolve().parent.parent.parent.parent / "application.yaml"


def load_lex_config() -> dict:
    """Load the full ``application.yaml`` config as a plain dict.

    Returns:
        Parsed YAML configuration dictionary.
    """
    return yaml.safe_load(APP_YAML.read_text())


@dataclass(init=False)
class SamplingConfig(BaseConfig):
    """Sampling parameters for LLM relay experiments.

    Controls temperature, top_p, and max_tokens for the relay mapper.
    All values are seeded and deterministic by construction.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    temperature: float = Field(
        default=0.7,
        description="Sampling temperature (0.0 = deterministic, 1.0 = max entropy)",
    )
    top_p: float = Field(
        default=0.9,
        description="Nucleus sampling threshold",
    )
    max_tokens: int = Field(
        default=1024,
        description="Maximum tokens in the relay response",
    )


@dataclass(init=False)
class ExperimentConfig(BaseConfig):
    """Root configuration for LLM reproducibility experiments.

    Aggregates sampling, model, seed, iterations, and recording
    configuration under a single ``experiment:`` section.
    """

    model_config = cast(
        "ConfigDict",
        {
            "env_prefix": "LEX_EXPERIMENT__",
            "env_nested_delimiter": "__",
            "extra": "ignore",
        },
    )

    config_section: ClassVar[str | None] = "experiment"

    name: str = Field(
        default="llm-reproducibility",
        description="Experiment name used in run_id generation",
    )
    description: str = Field(
        default="Deterministic reproducibility probe over the Claude relay mapper",
        description="Human-readable experiment description",
    )
    seed: int = Field(
        default=42,
        description="PRNG seed; same seed reproduces the run exactly",
    )
    iterations: int = Field(
        default=5,
        description="Number of seeded iterations per run",
    )
    provider: str = Field(
        default="anthropic",
        description="LLM provider name (for labels and metrics)",
    )
    model: str = Field(
        default="claude-3-5-sonnet",
        description="Model identifier exercised by the relay mapper",
    )
    sampling: SamplingConfig = Field(
        default_factory=SamplingConfig,
        description="Sampling parameters (temperature, top_p, max_tokens)",
    )
    tracing_enabled: bool = Field(
        default=True,
        description="Enable OpenTelemetry AITracer span recording",
    )
    metrics_enabled: bool = Field(
        default=True,
        description="Enable AIMetrics counter/histogram recording",
    )
