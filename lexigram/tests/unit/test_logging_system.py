"""Tests for Logging System Hardening (Phase 3).

Covers:
- configure_logging() core functionality
- Per-logger level overrides
- Deterministic log sampling
- LoggingConfig / SamplingConfig models
- apply_config() integration
- get_logger() with .name attribute
"""

from __future__ import annotations

import pytest
import structlog

from lexigram.logging import apply_config, configure_logging, get_logger, reset_logging
from lexigram.logging.config import LoggingConfig, RedactionConfig, SamplingConfig

# ---------------------------------------------------------------------------
# Stdlib bridge
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _cleanup_stdlib_handlers() -> None:
    """Remove handlers added by TestStdlibBridge to avoid cross-test pollution."""
    yield
    reset_logging()


class TestStdlibBridge:
    """Test that stdlib logging is bridged into structlog's pipeline."""

    def test_stdlib_logger_output_after_configure_logging(self, capsys: pytest.CaptureFixture[str]) -> None:
        """After configure_logging, stdlib loggers write structured output."""
        import logging

        configure_logging(level="DEBUG", json_format=True)

        stdlib_logger = logging.getLogger("test_stdlib_bridge")
        stdlib_logger.info("bridge test message")

        captured = capsys.readouterr()
        assert "bridge test message" in captured.out + captured.err

    def test_stdlib_logger_respects_level(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Stdlib handler respects the configured log level."""
        import logging

        configure_logging(level="WARNING", json_format=True)

        stdlib_logger = logging.getLogger("test_stdlib_level")
        stdlib_logger.info("should not appear")
        stdlib_logger.warning("should appear")

        captured = capsys.readouterr()
        outerr = captured.out + captured.err
        assert "should not appear" not in outerr
        assert "should appear" in outerr

# ---------------------------------------------------------------------------
# Basic configure_logging
# ---------------------------------------------------------------------------


class TestConfigureLogging:
    """Test core configure_logging() functionality."""

    def test_default_configuration(self) -> None:
        """configure_logging() runs without errors using defaults."""
        configure_logging()

    def test_json_format(self) -> None:
        """configure_logging(json_format=True) configures JSON renderer."""
        configure_logging(json_format=True)
        # Verify structlog config has JSONRenderer
        cfg = structlog.get_config()
        renderer_types = [type(p).__name__ for p in cfg["processors"]]
        assert "JSONRenderer" in renderer_types

    def test_console_format(self) -> None:
        """configure_logging(json_format=False) configures ConsoleRenderer."""
        configure_logging(json_format=False)
        cfg = structlog.get_config()
        renderer_types = [type(p).__name__ for p in cfg["processors"]]
        assert "ConsoleRenderer" in renderer_types

    def test_level_setting(self) -> None:
        """Global level is applied to the wrapper class."""
        configure_logging(level="DEBUG")
        # Should not raise — just verify it completes
        configure_logging(level="ERROR")


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------


class TestGetLogger:
    """Test get_logger() behavior and .name attribute."""

    def test_default_logger_name(self) -> None:
        """get_logger(None) returns a logger with name 'lexigram'."""
        logger = get_logger()
        assert hasattr(logger, "name")
        assert logger.name == "lexigram"

    def test_auto_prefix(self) -> None:
        """get_logger('mymodule') prepends 'lexigram.' prefix."""
        logger = get_logger("mymodule")
        assert logger.name == "lexigram.mymodule"

    def test_no_double_prefix(self) -> None:
        """get_logger('lexigram.di') does not double-prefix."""
        logger = get_logger("lexigram.di")
        assert logger.name == "lexigram.di"

    def test_logger_has_standard_methods(self) -> None:
        """Logger exposes standard log methods."""
        logger = get_logger("test")
        for method in ("debug", "info", "warning", "error"):
            assert hasattr(logger, method), f"Logger missing '{method}' method"


# ---------------------------------------------------------------------------
# Per-logger level overrides
# ---------------------------------------------------------------------------


class TestPerLoggerLevels:
    """Test per-logger level filtering via _level_filter_processor."""

    def test_levels_parameter_accepted(self) -> None:
        """configure_logging() accepts 'levels' parameter."""
        configure_logging(
            level="INFO",
            levels={"lexigram.di": "DEBUG", "lexigram.web": "WARNING"},
        )

    def test_level_filter_drops_below_threshold(self) -> None:
        """Events below per-logger level are dropped."""
        from lexigram.logging.processors import _level_filter_processor

        configure_logging(
            level="DEBUG",  # global allows DEBUG
            levels={"lexigram.noisy": "WARNING"},  # but noisy module is WARNING
        )

        event_dict = {"event": "test", "logger": "lexigram.noisy"}
        # DEBUG event for a WARNING-level logger should be dropped
        with pytest.raises(structlog.DropEvent):
            _level_filter_processor(None, "debug", event_dict)

    def test_level_filter_passes_above_threshold(self) -> None:
        """Events at or above per-logger level pass through."""
        from lexigram.logging.processors import _level_filter_processor

        configure_logging(
            level="DEBUG",
            levels={"lexigram.noisy": "WARNING"},
        )

        event_dict = {"event": "test", "logger": "lexigram.noisy"}
        result = _level_filter_processor(None, "error", event_dict)
        assert result is event_dict

    def test_level_filter_ignores_unconfigured_loggers(self) -> None:
        """Loggers without per-logger overrides are not filtered."""
        from lexigram.logging.processors import _level_filter_processor

        configure_logging(
            level="DEBUG",
            levels={"lexigram.noisy": "WARNING"},
        )

        event_dict = {"event": "test", "logger": "lexigram.other"}
        result = _level_filter_processor(None, "debug", event_dict)
        assert result is event_dict

    def test_level_filter_matches_prefix(self) -> None:
        """Per-logger level matches logger name prefixes."""
        from lexigram.logging.processors import _level_filter_processor

        configure_logging(
            level="DEBUG",
            levels={"lexigram.di": "ERROR"},
        )

        # Sub-logger should inherit the prefix rule
        event_dict = {"event": "test", "logger": "lexigram.di.container"}
        with pytest.raises(structlog.DropEvent):
            _level_filter_processor(None, "warning", event_dict)

    def test_no_levels_means_no_filtering(self) -> None:
        """When no levels are configured, processor is a no-op."""
        from lexigram.logging.processors import _level_filter_processor

        configure_logging(level="DEBUG")  # no levels param

        event_dict = {"event": "test", "logger": "lexigram.anything"}
        result = _level_filter_processor(None, "debug", event_dict)
        assert result is event_dict


# ---------------------------------------------------------------------------
# Log sampling
# ---------------------------------------------------------------------------


class TestLogSampling:
    """Test deterministic log sampling via _sampling_processor."""

    def test_sampling_disabled_by_default(self) -> None:
        """Sampling is disabled by default — all events pass."""
        from lexigram.logging.processors import _sampling_processor

        configure_logging()  # defaults: sampling_enabled=False

        event_dict = {"event": "high_volume"}
        result = _sampling_processor(None, "info", event_dict)
        assert result is event_dict

    def test_sampling_always_passes_warnings(self) -> None:
        """WARNING+ events are never sampled, even at rate=0."""
        from lexigram.logging.processors import _sampling_processor

        configure_logging(
            sampling_enabled=True,
            sampling_default_rate=0.0,  # drop everything
        )

        event_dict = {"event": "critical_failure"}
        result = _sampling_processor(None, "warning", event_dict)
        assert result is event_dict

        result = _sampling_processor(None, "error", event_dict)
        assert result is event_dict

        result = _sampling_processor(None, "critical", event_dict)
        assert result is event_dict

    def test_sampling_rate_zero_drops_debug_info(self) -> None:
        """rate=0.0 drops all DEBUG/INFO events."""
        from lexigram.logging.processors import _sampling_processor

        configure_logging(
            sampling_enabled=True,
            sampling_default_rate=0.0,
        )

        event_dict = {"event": "chatty_event"}
        with pytest.raises(structlog.DropEvent):
            _sampling_processor(None, "debug", event_dict)

        with pytest.raises(structlog.DropEvent):
            _sampling_processor(None, "info", event_dict)

    def test_sampling_rate_1_passes_all(self) -> None:
        """rate=1.0 passes all events (no sampling)."""
        from lexigram.logging.processors import _sampling_processor

        configure_logging(
            sampling_enabled=True,
            sampling_default_rate=1.0,
        )

        event_dict = {"event": "any_event"}
        result = _sampling_processor(None, "info", event_dict)
        assert result is event_dict

    def test_sampling_per_event_rule(self) -> None:
        """Per-event rules override default rate."""
        from lexigram.logging.processors import _sampling_processor

        configure_logging(
            sampling_enabled=True,
            sampling_default_rate=1.0,  # default: pass all
            sampling_rules={"drop_me": 0.0},  # but this event: drop all
        )

        event_dict = {"event": "drop_me"}
        with pytest.raises(structlog.DropEvent):
            _sampling_processor(None, "info", event_dict)

        # Other events still pass
        event_dict_ok = {"event": "keep_me"}
        result = _sampling_processor(None, "info", event_dict_ok)
        assert result is event_dict_ok

    def test_sampling_is_deterministic(self) -> None:
        """Same event key always produces same include/exclude decision."""
        from lexigram.logging.processors import _sampling_processor

        configure_logging(
            sampling_enabled=True,
            sampling_default_rate=0.5,
        )

        # Run the same event 100 times — should always get the same result
        event_dict = {"event": "deterministic_test"}
        results = []
        for _ in range(100):
            try:
                _sampling_processor(None, "info", dict(event_dict))
                results.append(True)
            except structlog.DropEvent:
                results.append(False)

        # All results should be the same (deterministic)
        assert len(set(results)) == 1


# ---------------------------------------------------------------------------
# LoggingConfig model
# ---------------------------------------------------------------------------


class TestLoggingConfigModel:
    """Test LoggingConfig and SamplingConfig models."""

    def test_default_values(self) -> None:
        """LoggingConfig has sensible defaults."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.json_format is False
        assert config.levels == {}
        assert isinstance(config.sampling, SamplingConfig)
        assert isinstance(config.redaction, RedactionConfig)
        assert config.redaction.enabled is True

    def test_sampling_config_defaults(self) -> None:
        """SamplingConfig has sensible defaults."""
        sampling = SamplingConfig()
        assert sampling.enabled is False
        assert sampling.default_rate == 1.0
        assert sampling.rules == {}

    def test_logging_config_with_levels(self) -> None:
        """LoggingConfig accepts per-logger levels."""
        config = LoggingConfig(
            level="DEBUG",
            levels={"lexigram.di": "WARNING"},
        )
        assert config.levels == {"lexigram.di": "WARNING"}

    def test_logging_config_with_sampling(self) -> None:
        """LoggingConfig accepts nested SamplingConfig."""
        config = LoggingConfig(
            sampling=SamplingConfig(enabled=True, default_rate=0.5),
        )
        assert config.sampling.enabled is True
        assert config.sampling.default_rate == 0.5

    def test_logging_config_with_redaction(self) -> None:
        """LoggingConfig accepts nested RedactionConfig."""
        config = LoggingConfig(
            redaction=RedactionConfig(enabled=False, field_denylist=("a",)),
        )
        assert config.redaction.enabled is False
        assert config.redaction.field_denylist == ("a",)

    def test_logging_config_redaction_from_dict(self) -> None:
        """LoggingConfig redaction can be constructed from nested dict."""
        config = LoggingConfig(
            redaction={"enabled": False, "field_denylist": ("a",)},
        )
        assert config.redaction.enabled is False
        assert config.redaction.field_denylist == ("a",)

    def test_logging_config_from_dict(self) -> None:
        """LoggingConfig can be constructed from nested dict."""
        config = LoggingConfig(
            level="WARNING",
            sampling={"enabled": True, "default_rate": 0.1},
        )
        assert config.sampling.enabled is True
        assert config.sampling.default_rate == 0.1

    def test_invalid_level_normalized(self) -> None:
        """Invalid log level is normalized to INFO."""
        config = LoggingConfig(level="NOPE")
        assert config.level == "INFO"

    def test_no_file_field(self) -> None:
        """LoggingConfig no longer has a 'file' field (removed Phase 2)."""
        dc_fields = getattr(LoggingConfig, "__dataclass_fields__", {})
        assert "file" not in dc_fields

    def test_no_stream_field(self) -> None:
        """LoggingConfig no longer has a 'stream' field (removed Phase 2)."""
        dc_fields = getattr(LoggingConfig, "__dataclass_fields__", {})
        assert "stream" not in dc_fields


# ---------------------------------------------------------------------------
# apply_config integration
# ---------------------------------------------------------------------------


class TestApplyConfig:
    """Test apply_config() integrates LoggingConfig with configure_logging()."""

    def test_basic_apply(self) -> None:
        """apply_config() calls configure_logging() with correct args."""
        config = LoggingConfig(level="DEBUG", json_format=True)
        apply_config(config)
        # If we got here without error, it worked

    def test_apply_with_levels(self) -> None:
        """apply_config() passes per-logger levels through."""
        config = LoggingConfig(
            levels={"lexigram.di": "ERROR"},
        )
        apply_config(config)

        from lexigram.logging.processors import _state
        assert "lexigram.di" in _state.logger_levels

    def test_apply_with_sampling(self) -> None:
        """apply_config() passes sampling config through."""
        config = LoggingConfig(
            sampling=SamplingConfig(enabled=True, default_rate=0.5),
        )
        apply_config(config)

        from lexigram.logging.processors import _state
        assert _state.sampling_enabled is True
        assert _state.sampling_default_rate == 0.5

    def test_apply_redaction_enabled_default(self) -> None:
        """apply_config() installs a DefaultRedactor by default."""
        config = LoggingConfig()
        apply_config(config)

        from lexigram.logging.redaction import DefaultRedactor, get_redactor
        assert isinstance(get_redactor(), DefaultRedactor)

    def test_apply_redaction_explicit_enabled(self) -> None:
        """apply_config() installs a DefaultRedactor when enabled."""
        config = LoggingConfig(redaction=RedactionConfig(enabled=True))
        apply_config(config)

        from lexigram.logging.redaction import DefaultRedactor, get_redactor
        assert isinstance(get_redactor(), DefaultRedactor)

    def test_apply_redaction_disabled(self) -> None:
        """apply_config() installs a NoOpRedactor when disabled."""
        config = LoggingConfig(redaction=RedactionConfig(enabled=False))
        apply_config(config)

        from lexigram.logging.redaction import NoOpRedactor, get_redactor
        assert isinstance(get_redactor(), NoOpRedactor)

    def test_apply_redaction_custom_denylist(self) -> None:
        """apply_config() forwards a custom field denylist."""
        config = LoggingConfig(
            redaction=RedactionConfig(enabled=True, field_denylist=("ssn",)),
        )
        apply_config(config)

        from lexigram.logging.redaction import DefaultRedactor, get_redactor
        redactor = get_redactor()
        assert isinstance(redactor, DefaultRedactor)
        assert redactor._field_denylist == frozenset({"ssn"})


# ---------------------------------------------------------------------------
# End-to-end redaction through the real pipeline
# ---------------------------------------------------------------------------


class TestRedactionE2E:
    """Prove redaction works through the full structlog pipeline."""

    def test_password_field_redacted(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A denylisted key is masked in JSON output."""
        configure_logging(level="DEBUG", json_format=True)

        logger = get_logger()
        logger.info("payment_failed", password="hunter2", user_id=7)

        captured = capsys.readouterr()
        outerr = captured.out + captured.err
        assert "<redacted>" in outerr
        assert "hunter2" not in outerr

    def test_nested_key_redacted(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Nested denylisted keys are masked recursively."""
        configure_logging(level="DEBUG", json_format=True)

        logger = get_logger()
        logger.info("request_started", metadata={"api_key": "x", "user": "bob"})

        captured = capsys.readouterr()
        outerr = captured.out + captured.err
        assert "<redacted>" in outerr
        assert '"x"' not in outerr
        assert "bob" in outerr

    def test_redaction_disabled_passes_raw(self, capsys: pytest.CaptureFixture[str]) -> None:
        """configure_logging(redaction_enabled=False) passes raw values."""
        configure_logging(level="DEBUG", json_format=True, redaction_enabled=False)

        logger = get_logger()
        logger.info("payment_failed", password="hunter2")

        captured = capsys.readouterr()
        outerr = captured.out + captured.err
        assert "<redacted>" not in outerr
        assert "hunter2" in outerr
