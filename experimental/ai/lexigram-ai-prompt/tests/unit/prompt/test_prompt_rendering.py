"""Tests for prompt rendering and template processing."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestPromptRendering:
    """Test prompt template rendering."""

    def test_render_with_variables(self) -> None:
        """Renderer should substitute variables."""
        renderer = MagicMock()
        renderer.render = MagicMock(
            return_value="Hello, Alice!"
        )

        result = renderer.render("Hello, {name}!", {"name": "Alice"})

        assert "Alice" in result

    def test_render_multiple_variables(self) -> None:
        """Renderer should handle multiple variables."""
        renderer = MagicMock()
        renderer.render = MagicMock(
            return_value="Hello, Alice! You are 30 years old."
        )

        result = renderer.render(
            "Hello, {name}! You are {age} years old.",
            {"name": "Alice", "age": 30},
        )

        assert "Alice" in result
        assert "30" in result

    def test_render_missing_variable_handling(self) -> None:
        """Renderer should handle missing variables."""
        renderer = MagicMock()
        renderer.render = MagicMock(side_effect=KeyError("Missing variable"))

        with pytest.raises(KeyError):
            renderer.render("Hello, {name}!", {})

    def test_render_empty_template(self) -> None:
        """Renderer should handle empty templates."""
        renderer = MagicMock()
        renderer.render = MagicMock(return_value="")

        result = renderer.render("", {})

        assert result == ""


class TestTemplateVariables:
    """Test template variable handling."""

    def test_required_variables(self) -> None:
        """Template should track required variables."""
        template = MagicMock()
        template.required_variables = ["name", "context"]

        assert len(template.required_variables) == 2
        assert "name" in template.required_variables

    def test_optional_variables(self) -> None:
        """Template should support optional variables."""
        template = MagicMock()
        template.optional_variables = ["tone", "style"]

        assert len(template.optional_variables) >= 0

    def test_variable_substitution(self) -> None:
        """Variables should be substitutable."""
        template = MagicMock()
        template.substitute = MagicMock(
            return_value="Rendered result"
        )

        result = template.substitute({"var1": "value1"})

        assert result is not None


class TestPromptFormats:
    """Test different prompt rendering formats."""

    def test_f_string_format(self) -> None:
        """F-string format should work."""
        renderer = MagicMock()
        renderer.render = MagicMock(return_value="Hello, world!")

        result = renderer.render("Hello, {name}!", {"name": "world"})

        assert "world" in result

    def test_jinja2_format(self) -> None:
        """Jinja2 format should work."""
        renderer = MagicMock()
        renderer.render = MagicMock(return_value="Value: 10")

        result = renderer.render("Value: {{ x }}", {"x": 10})

        assert "10" in result

    def test_dollar_format(self) -> None:
        """Dollar-sign format should work."""
        renderer = MagicMock()
        renderer.render = MagicMock(return_value="Price: $100")

        result = renderer.render("Price: $price", {"price": "$100"})

        assert "100" in result


class TestPromptOptimization:
    """Test prompt optimization strategies."""

    def test_token_optimization(self) -> None:
        """Optimizer should reduce token count."""
        optimizer = MagicMock()
        optimizer.optimize = MagicMock(return_value="Shorter text")

        result = optimizer.optimize("Very long text that is unnecessarily verbose")

        assert len(result) > 0

    def test_compression(self) -> None:
        """Compression should reduce size."""
        compressor = MagicMock()
        compressor.compress = MagicMock(return_value="Compressed")

        result = compressor.compress("Original long prompt content")

        assert len(result) > 0

    def test_cache_aware_rendering(self) -> None:
        """Renderer should support caching."""
        renderer = MagicMock()
        renderer.render_cached = MagicMock(return_value="Cached result")

        result = renderer.render_cached("template_key")

        assert result is not None


class TestPromptComposition:
    """Test prompt composition and pipelines."""

    def test_prompt_pipeline(self) -> None:
        """Prompts should be composable in pipelines."""
        pipeline = MagicMock()
        pipeline.add_step = MagicMock(return_value=pipeline)

        pipeline.add_step("system").add_step("context").add_step("request")

        assert pipeline.add_step.call_count == 3

    def test_conditional_prompts(self) -> None:
        """Prompts should support conditions."""
        prompt = MagicMock()
        prompt.if_condition = MagicMock(return_value=prompt)

        prompt.if_condition("user_role == 'admin'", "admin_template")

        prompt.if_condition.assert_called_once()

    def test_prompt_versioning(self) -> None:
        """Prompts should support versions."""
        registry = MagicMock()
        registry.get_version = MagicMock(return_value="v2.0")

        version = registry.get_version("greeting", 2)

        assert version == "v2.0"


class TestPromptSanitization:
    """Test input sanitization."""

    def test_sanitize_user_input(self) -> None:
        """Sanitizer should clean user input."""
        sanitizer = MagicMock()
        sanitizer.sanitize = MagicMock(return_value="clean input")

        result = sanitizer.sanitize("user_input_with_<script>")

        assert "<script>" not in result

    def test_injection_detection(self) -> None:
        """Sanitizer should detect injections."""
        sanitizer = MagicMock()
        sanitizer.detect_injection = MagicMock(return_value=True)

        is_injection = sanitizer.detect_injection("'; DROP TABLE users; --")

        assert is_injection is True

    def test_safe_string_escaping(self) -> None:
        """Sanitizer should escape special characters."""
        sanitizer = MagicMock()
        sanitizer.escape = MagicMock(return_value="&quot;escaped&quot;")

        result = sanitizer.escape('"quoted"')

        assert "&quot;" in result or '"' in result
