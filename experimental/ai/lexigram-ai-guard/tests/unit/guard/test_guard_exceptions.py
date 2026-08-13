"""Tests for AI guard exceptions."""


def test_guard_error_is_exception() -> None:
    from lexigram.ai.guard.exceptions import GuardError
    assert issubclass(GuardError, Exception)


def test_guard_configuration_error_is_guard_error() -> None:
    from lexigram.ai.guard.exceptions import GuardError, GuardConfigurationError
    assert issubclass(GuardConfigurationError, GuardError)


def test_guard_pipeline_error_is_guard_error() -> None:
    from lexigram.ai.guard.exceptions import GuardError, GuardPipelineError
    assert issubclass(GuardPipelineError, GuardError)


def test_guard_error_creation() -> None:
    from lexigram.ai.guard.exceptions import GuardError
    exc = GuardError("test error")
    assert "test error" in str(exc)


def test_guard_configuration_error_creation() -> None:
    from lexigram.ai.guard.exceptions import GuardConfigurationError
    exc = GuardConfigurationError("config error")
    assert "config error" in str(exc)


def test_guard_pipeline_error_creation() -> None:
    from lexigram.ai.guard.exceptions import GuardPipelineError
    exc = GuardPipelineError("pipeline error")
    assert "pipeline error" in str(exc)
