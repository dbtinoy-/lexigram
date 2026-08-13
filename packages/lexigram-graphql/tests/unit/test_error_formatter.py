from __future__ import annotations

from lexigram.graphql.config import ErrorConfig
from lexigram.graphql.core.error_formatter import ErrorFormatter, create_error_formatter
from lexigram.graphql.exceptions import GraphQLError
from lexigram.graphql.types import GraphQLErrorCode


class _SafeError(GraphQLError):
    safe = True


class _DetailedError(GraphQLError):
    code = GraphQLErrorCode.BAD_USER_INPUT
    details: str = ""
    hint: str = ""


class TestErrorFormatter:
    def test_format_graphql_error(self) -> None:
        config = ErrorConfig(mask_errors=False)
        formatter = ErrorFormatter(config)
        error = GraphQLError(message="Something broke", code=GraphQLErrorCode.INTERNAL_SERVER_ERROR)
        result = formatter.format_error(error)
        assert result["message"] == "Something broke"
        assert "code" in result["extensions"]

    def test_format_graphql_error_with_details(self) -> None:
        config = ErrorConfig(mask_errors=False)
        formatter = ErrorFormatter(config)
        error = _DetailedError(
            message="Validation failed",
        )
        error.details = "Field 'name' is required"
        error.hint = "Provide a value for 'name'"
        result = formatter.format_error(error)
        assert result["extensions"]["details"] == "Field 'name' is required"
        assert result["extensions"]["hint"] == "Provide a value for 'name'"

    def test_masks_errors_in_production(self) -> None:
        config = ErrorConfig(mask_errors=True, debug_mode=False)
        formatter = ErrorFormatter(config)
        error = GraphQLError(message="Secret internal error")
        result = formatter.format_error(error)
        assert result["message"] == "Internal server error"

    def test_safe_error_not_masked(self) -> None:
        config = ErrorConfig(mask_errors=True, debug_mode=False)
        formatter = ErrorFormatter(config)
        error = _SafeError(message="Safe user error")
        result = formatter.format_error(error)
        assert result["message"] == "Safe user error"

    def test_plain_exception_formatted(self) -> None:
        config = ErrorConfig(mask_errors=False)
        formatter = ErrorFormatter(config)
        result = formatter.format_error(ValueError("plain error"))
        assert "plain error" in result["message"]

    def test_stacktrace_in_debug_mode(self) -> None:
        config = ErrorConfig(mask_errors=False, debug_mode=True, include_stacktrace=True)
        formatter = ErrorFormatter(config)
        try:
            raise ValueError("debug error")
        except ValueError as e:
            result = formatter.format_error(e)
        assert "stacktrace" in result["extensions"]

    def test_format_errors_list(self) -> None:
        config = ErrorConfig(mask_errors=False)
        formatter = ErrorFormatter(config)
        errors = [
            GraphQLError(message="Error 1"),
            GraphQLError(message="Error 2"),
        ]
        results = formatter.format_errors(errors)
        assert len(results) == 2
        assert results[0]["message"] == "Error 1"
        assert results[1]["message"] == "Error 2"

    def test_create_error_formatter_default(self) -> None:
        formatter = create_error_formatter()
        assert isinstance(formatter, ErrorFormatter)

    def test_plain_exception_with_extensions(self) -> None:
        config = ErrorConfig(mask_errors=False)
        formatter = ErrorFormatter(config)

        class ExtError(Exception):
            extensions = {"custom": "data"}

        result = formatter.format_error(ExtError("has ext"))
        assert result["extensions"]["custom"] == "data"


class TestErrorFormatterInitialization:
    def test_default_config(self) -> None:
        formatter = ErrorFormatter(ErrorConfig())
        assert formatter._config is not None
