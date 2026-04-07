"""Tests for AI prompt exceptions."""


def test_prompt_error_is_exception() -> None:
    from lexigram.ai.prompt.exceptions import PromptError
    assert issubclass(PromptError, Exception)


def test_prompt_render_error_is_prompt_error() -> None:
    from lexigram.ai.prompt.exceptions import PromptError, PromptRenderError
    assert issubclass(PromptRenderError, PromptError)


def test_prompt_validation_error_is_prompt_error() -> None:
    from lexigram.ai.prompt.exceptions import PromptError, PromptValidationError
    assert issubclass(PromptValidationError, PromptError)


def test_prompt_not_found_error_is_prompt_error() -> None:
    from lexigram.ai.prompt.exceptions import PromptError, PromptNotFoundError
    assert issubclass(PromptNotFoundError, PromptError)


def test_prompt_version_error_is_prompt_error() -> None:
    from lexigram.ai.prompt.exceptions import PromptError, PromptVersionError
    assert issubclass(PromptVersionError, PromptError)


def test_prompt_config_error_is_prompt_error() -> None:
    from lexigram.ai.prompt.exceptions import PromptError, PromptConfigError
    assert issubclass(PromptConfigError, PromptError)


def test_prompt_error_creation() -> None:
    from lexigram.ai.prompt.exceptions import PromptError
    exc = PromptError("test error")
    assert "test error" in str(exc)


def test_prompt_render_error_creation() -> None:
    from lexigram.ai.prompt.exceptions import PromptRenderError
    exc = PromptRenderError("render error")
    assert "render error" in str(exc)


def test_prompt_validation_error_creation() -> None:
    from lexigram.ai.prompt.exceptions import PromptValidationError
    exc = PromptValidationError("validation error")
    assert "validation error" in str(exc)


def test_prompt_not_found_error_creation() -> None:
    from lexigram.ai.prompt.exceptions import PromptNotFoundError
    exc = PromptNotFoundError("not found error")
    assert "not found error" in str(exc)


def test_prompt_version_error_creation() -> None:
    from lexigram.ai.prompt.exceptions import PromptVersionError
    exc = PromptVersionError("version error")
    assert "version error" in str(exc)


def test_prompt_config_error_creation() -> None:
    from lexigram.ai.prompt.exceptions import PromptConfigError
    exc = PromptConfigError("config error")
    assert "config error" in str(exc)
