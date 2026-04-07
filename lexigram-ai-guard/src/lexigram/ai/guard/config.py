"""GuardProtocol configuration for the Lexigram framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from lexigram.ai.guard.constants import ENV_NESTED_DELIMITER, ENV_PREFIX
from lexigram.config.base import BaseConfig
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class GuardConfig(BaseConfig):
    """Configuration for the content safety guard pipeline.

    Controls which guards are enabled by default and their behaviour.
    Guards can be further customised programmatically via
    :class:`~lexigram.ai.guard.pipeline.guard_pipeline.GuardPipeline`.

    Attributes:
        enabled: Master switch — when ``False`` the guard pipeline is
                 bypassed entirely.
        injection_detection: Enable the prompt injection detector.
        injection_action: Action on detected injection (``"block"``/``"warn"``).
        pii_detection: Enable PII detection on inputs.
        pii_action: Action on detected PII (``"redact"``/``"block"``/``"warn"``).
        pii_entities: PII entity types to detect.  Empty list means all types.
        pii_redaction_output: Enable PII redaction on LLM outputs.
        max_input_chars: Maximum allowed input length in characters.
                         ``0`` disables the length guard.
        max_output_chars: Maximum allowed output length in characters.
                          ``0`` disables the output length guard.
        length_action: Action when length limit exceeded (``"block"``/``"warn"``).
        restricted_topics: Topics to block in user inputs.
    """

    config_section: ClassVar[str] = "ai_guard"

    model_config: ClassVar[ConfigDict] = ConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix=ENV_PREFIX,
        env_nested_delimiter=ENV_NESTED_DELIMITER,
        extra="ignore",
    )

    enabled: bool = Field(default=True)
    """Master on/off switch for the guard pipeline."""

    injection_detection: bool = Field(default=True)
    """Enable prompt injection detector on all inputs."""

    injection_action: str = Field(default="block")
    """Action when injection is detected: ``"block"`` or ``"warn"``."""

    pii_detection: bool = Field(default=True)
    """Enable PII detection on user inputs."""

    pii_action: str = Field(default="redact")
    """Action when PII is detected: ``"redact"``, ``"block"``, or ``"warn"``."""

    pii_entities: list[str] = field(default_factory=list)
    """PII entity types to scan for.  Empty = all types."""

    pii_redaction_output: bool = Field(default=True)
    """Enable PII redaction on LLM outputs."""

    max_input_chars: int = Field(default=0, ge=0)
    """Maximum input length in characters.  ``0`` = unlimited."""

    max_output_chars: int = Field(default=0, ge=0)
    """Maximum output length in characters.  ``0`` = unlimited."""

    length_action: str = Field(default="block")
    """Action when input or output length limit exceeded."""

    restricted_topics: list[str] = field(default_factory=list)
    """Topic keywords/phrases to block in user inputs."""

    enable_llm_guards: bool = Field(default=False)
    """Enable LLM-based injection and jailbreak detection guards.

    When ``True`` and an ``LLMClientProtocol`` is available in the container,
    :class:`~lexigram.ai.guard.input.llm_injection.LLMInjectionDetector` and
    :class:`~lexigram.ai.guard.input.llm_jailbreak.LLMJailbreakDetector` are
    added to the pipeline after the heuristic guards.
    """

    guard_model: str = Field(default="gpt-4o-mini")
    """Model to use for LLM-based guards (should be a fast, small model)."""

    llm_guard_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    """Confidence threshold above which LLM guards trigger their action."""

    sensitivity_level: str = Field(default="medium")
    """Guard sensitivity: ``"low"``, ``"medium"``, or ``"high"``.

    Controls how aggressively guards flag content:
    - ``"low"`` — only flag obvious violations.
    - ``"medium"`` — balanced detection (default).
    - ``"high"`` — aggressive detection, may produce more false positives.
    """

    parallel_execution: bool = Field(default=False)
    """Run guards concurrently with asyncio.gather instead of sequentially.

    When enabled, redaction chaining is disabled — each guard receives
    the original content.  Useful when guards are independent and I/O-bound.
    """


__all__ = ["GuardConfig"]
