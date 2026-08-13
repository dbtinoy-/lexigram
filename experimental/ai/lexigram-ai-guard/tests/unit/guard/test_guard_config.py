"""Tests for guard configuration."""

import pytest

from lexigram.ai.guard.config import GuardConfig


class TestGuardConfig:
    """Tests for GuardConfig."""

    def test_default_config(self) -> None:
        """Test default guard configuration."""
        config = GuardConfig()
        assert config.enabled is True
        assert config.injection_detection is True
        assert config.injection_action == "block"
        assert config.pii_detection is True
        assert config.pii_action == "redact"
        assert config.pii_entities == []
        assert config.pii_redaction_output is True
        assert config.max_input_chars == 0
        assert config.max_output_chars == 0
        assert config.length_action == "block"
        assert config.restricted_topics == []

    def test_disable_guards(self) -> None:
        """Test disabling all guards."""
        config = GuardConfig(enabled=False)
        assert config.enabled is False

    def test_disable_injection_detection(self) -> None:
        """Test disabling injection detection."""
        config = GuardConfig(injection_detection=False)
        assert config.injection_detection is False

    def test_injection_action_warn(self) -> None:
        """Test setting injection action to warn."""
        config = GuardConfig(injection_action="warn")
        assert config.injection_action == "warn"

    def test_disable_pii_detection(self) -> None:
        """Test disabling PII detection."""
        config = GuardConfig(pii_detection=False)
        assert config.pii_detection is False

    def test_pii_action_block(self) -> None:
        """Test setting PII action to block."""
        config = GuardConfig(pii_action="block")
        assert config.pii_action == "block"

    def test_pii_action_warn(self) -> None:
        """Test setting PII action to warn."""
        config = GuardConfig(pii_action="warn")
        assert config.pii_action == "warn"

    def test_custom_pii_entities(self) -> None:
        """Test configuring custom PII entities."""
        config = GuardConfig(pii_entities=["email", "ssn", "phone"])
        assert config.pii_entities == ["email", "ssn", "phone"]

    def test_disable_pii_redaction_output(self) -> None:
        """Test disabling PII redaction on output."""
        config = GuardConfig(pii_redaction_output=False)
        assert config.pii_redaction_output is False

    def test_custom_max_input_chars(self) -> None:
        """Test configuring max input characters."""
        config = GuardConfig(max_input_chars=10000)
        assert config.max_input_chars == 10000

    def test_max_input_chars_zero(self) -> None:
        """Test that zero max_input_chars means unlimited."""
        config = GuardConfig(max_input_chars=0)
        assert config.max_input_chars == 0

    def test_max_input_chars_negative(self) -> None:
        """Test that max_input_chars cannot be negative."""
        with pytest.raises(ValueError):
            GuardConfig(max_input_chars=-1)

    def test_custom_max_output_chars(self) -> None:
        """Test configuring max output characters."""
        config = GuardConfig(max_output_chars=20000)
        assert config.max_output_chars == 20000

    def test_max_output_chars_negative(self) -> None:
        """Test that max_output_chars cannot be negative."""
        with pytest.raises(ValueError):
            GuardConfig(max_output_chars=-1)

    def test_length_action_warn(self) -> None:
        """Test setting length action to warn."""
        config = GuardConfig(length_action="warn")
        assert config.length_action == "warn"

    def test_restricted_topics(self) -> None:
        """Test configuring restricted topics."""
        config = GuardConfig(restricted_topics=["politics", "religion", "violence"])
        assert config.restricted_topics == ["politics", "religion", "violence"]

    def test_llm_guard_fail_open_default_false(self) -> None:
        """LLM guards fail closed on infrastructure errors by default."""
        config = GuardConfig()
        assert config.llm_guard_fail_open is False

    def test_llm_guard_fail_open_explicit_true(self) -> None:
        """Explicit True restores the legacy fully fail-open posture."""
        config = GuardConfig(llm_guard_fail_open=True)
        assert config.llm_guard_fail_open is True

    def test_full_custom_config(self) -> None:
        """Test configuring all options."""
        config = GuardConfig(
            enabled=True,
            injection_detection=True,
            injection_action="warn",
            pii_detection=True,
            pii_action="block",
            pii_entities=["email"],
            pii_redaction_output=False,
            max_input_chars=5000,
            max_output_chars=10000,
            length_action="warn",
            restricted_topics=["spam"],
        )
        assert config.enabled is True
        assert config.injection_detection is True
        assert config.injection_action == "warn"
        assert config.pii_detection is True
        assert config.pii_action == "block"
        assert config.pii_entities == ["email"]
        assert config.pii_redaction_output is False
        assert config.max_input_chars == 5000
        assert config.max_output_chars == 10000
        assert config.length_action == "warn"
        assert config.restricted_topics == ["spam"]
