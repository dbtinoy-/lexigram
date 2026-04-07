"""Unit tests for output guards."""

from __future__ import annotations

import pytest

from lexigram.ai.guard.output.length import OutputLengthGuard
from lexigram.ai.guard.output.pii_redactor import PIIRedactor
from lexigram.ai.guard.pipeline.result import GuardAction


# ---------------------------------------------------------------------------
# OutputLengthGuard
# ---------------------------------------------------------------------------


class TestOutputLengthGuard:
    @pytest.mark.asyncio
    async def test_within_limit_passes(self) -> None:
        guard = OutputLengthGuard(max_chars=1000)
        result = await guard.check("Short response.")
        assert result.unwrap().passed is True
        assert result.unwrap().action == GuardAction.PASS

    @pytest.mark.asyncio
    async def test_exactly_at_limit_passes(self) -> None:
        guard = OutputLengthGuard(max_chars=5)
        result = await guard.check("hello")
        assert result.unwrap().passed is True

    @pytest.mark.asyncio
    async def test_over_limit_blocks_by_default(self) -> None:
        guard = OutputLengthGuard(max_chars=5)
        result = await guard.check("this response is too long")
        assert result.unwrap().passed is False
        assert result.unwrap().action == GuardAction.BLOCK

    @pytest.mark.asyncio
    async def test_over_limit_warns_when_configured(self) -> None:
        guard = OutputLengthGuard(max_chars=5, action="warn")
        result = await guard.check("this is longer than five")
        assert result.unwrap().passed is True
        assert result.unwrap().action == GuardAction.WARN

    @pytest.mark.asyncio
    async def test_original_input_ignored(self) -> None:
        """original_input parameter should not affect the result."""
        guard = OutputLengthGuard(max_chars=1000)
        result = await guard.check("ok", original_input="some prompt")
        assert result.unwrap().passed is True

    def test_name_is_class_name(self) -> None:
        guard = OutputLengthGuard(max_chars=100)
        assert guard.name == "OutputLengthGuard"


# ---------------------------------------------------------------------------
# PIIRedactor
# ---------------------------------------------------------------------------


class TestPIIRedactor:
    @pytest.mark.asyncio
    async def test_clean_response_passes(self) -> None:
        guard = PIIRedactor()
        result = await guard.check("The answer to your question is 42.")
        assert result.unwrap().passed is True
        assert result.unwrap().action == GuardAction.PASS

    @pytest.mark.asyncio
    async def test_email_in_response_is_redacted(self) -> None:
        guard = PIIRedactor()
        result = await guard.check("You can reach support at help@company.io.")
        assert result.unwrap().action == GuardAction.REDACT
        assert result.unwrap().redacted_content is not None
        assert "help@company.io" not in result.unwrap().redacted_content
        assert "[REDACTED:EMAIL]" in result.unwrap().redacted_content

    @pytest.mark.asyncio
    async def test_ssn_in_response_is_redacted(self) -> None:
        guard = PIIRedactor(entities=["SSN"])
        # Use a non-excluded SSN prefix (not 000, 666, or 9xx)
        result = await guard.check("The applicant's SSN on file is 267-65-4321.")
        assert result.unwrap().action == GuardAction.REDACT
        rc = result.unwrap().redacted_content or ""
        assert "267-65-4321" not in rc

    @pytest.mark.asyncio
    async def test_block_action_rejects_pii_response(self) -> None:
        guard = PIIRedactor(action="block")
        result = await guard.check("Contact alice@example.com for more info.")
        assert result.unwrap().passed is False
        assert result.unwrap().action == GuardAction.BLOCK

    @pytest.mark.asyncio
    async def test_entity_subset_respects_scope(self) -> None:
        """Redactor scoped to EMAIL should not flag phone numbers."""
        guard = PIIRedactor(entities=["EMAIL"])
        result = await guard.check("Call us at 555-123-4567 today.")
        assert result.unwrap().action == GuardAction.PASS

    @pytest.mark.asyncio
    async def test_multiple_pii_in_response_all_redacted(self) -> None:
        guard = PIIRedactor()
        response = "Send your results to alice@example.com or call 555-123-4567."
        result = await guard.check(response)
        assert result.unwrap().action == GuardAction.REDACT
        rc = result.unwrap().redacted_content or ""
        assert "alice@example.com" not in rc
        assert "555-123-4567" not in rc

    def test_name_is_class_name(self) -> None:
        guard = PIIRedactor()
        assert guard.name == "PIIRedactor"
