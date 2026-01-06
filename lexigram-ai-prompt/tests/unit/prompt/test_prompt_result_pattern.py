"""Tests for Result pattern in prompt service."""

import pytest
from lexigram.contracts.ai.exceptions import AIError
from lexigram.ai.prompt.services.result_pattern_service import PromptServiceWithResultPattern

class TestPromptServiceResultPattern:
    """Test Result pattern in prompt service."""

    @pytest.fixture
    def prompt_service(self) -> PromptServiceWithResultPattern:
        """Create prompt service."""
        return PromptServiceWithResultPattern()

    @pytest.mark.asyncio
    async def test_render_returns_ok(self, prompt_service):
        """Verify render returns Ok."""
        result = await prompt_service.render("chat", {"user_input": "Hello"})
        assert result.is_ok()
        prompt = result.unwrap()
        assert isinstance(prompt, str)

    @pytest.mark.asyncio
    async def test_render_returns_err_for_empty_template(self, prompt_service):
        """Verify render returns Err for empty template name."""
        result = await prompt_service.render("", {"key": "value"})
        assert result.is_err()
        assert isinstance(result.unwrap_err(), AIError)
