"""Tests for prompt constants module."""

from __future__ import annotations

import pytest
from lexigram.ai.prompt import constants
from lexigram.ai.prompt.rendering.engine import RenderFormat


class TestConstants:
    """Tests for constant values."""

    def test_env_prefix(self) -> None:
        assert constants.ENV_PREFIX == "LEX_AI_PROMPT__"

    def test_env_nested_delimiter(self) -> None:
        assert constants.ENV_NESTED_DELIMITER == "__"

    def test_default_render_format(self) -> None:
        assert constants.DEFAULT_RENDER_FORMAT == RenderFormat.JINJA2

    def test_max_prompt_versions(self) -> None:
        assert constants.MAX_PROMPT_VERSIONS == 100

    def test_max_rendered_prompt_length(self) -> None:
        assert constants.MAX_RENDERED_PROMPT_LENGTH == 64_000

    def test_error_template_not_found(self) -> None:
        assert constants.ERROR_TEMPLATE_NOT_FOUND == "LEX_PROMPT_001"

    def test_error_variable_missing(self) -> None:
        assert constants.ERROR_VARIABLE_MISSING == "LEX_PROMPT_002"

    def test_error_render_failed(self) -> None:
        assert constants.ERROR_RENDER_FAILED == "LEX_PROMPT_003"


class TestVersion:
    """Tests for version constant."""

    def test_version_exists(self) -> None:
        assert hasattr(constants, "__version__")
        assert isinstance(constants.__version__, str)

    def test_version_format(self) -> None:
        version = constants.__version__
        parts = version.split(".")
        assert len(parts) >= 3
        assert parts[0].isdigit()
        assert parts[1].isdigit()
        assert parts[2].split("-")[0].isdigit()


class TestAllExports:
    """Verify all expected constants are exported."""

    def test_all_in_all_list(self) -> None:
        expected = [
            "DEFAULT_RENDER_FORMAT",
            "ENV_NESTED_DELIMITER",
            "ENV_PREFIX",
            "ERROR_RENDER_FAILED",
            "ERROR_TEMPLATE_NOT_FOUND",
            "ERROR_VARIABLE_MISSING",
            "MAX_PROMPT_VERSIONS",
            "MAX_RENDERED_PROMPT_LENGTH",
            "__version__",
        ]
        assert set(expected) == set(constants.__all__)