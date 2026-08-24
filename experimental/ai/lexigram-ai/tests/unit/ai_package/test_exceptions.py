"""Tests for lexigram.ai.exceptions."""

from __future__ import annotations

import pytest


class TestAIPackageException:
    """Tests for lexigram.ai.exceptions.AIError."""

    def test_ai_error_is_instantiable(self) -> None:
        from lexigram.ai.exceptions import AIError

        err = AIError("something went wrong in AI")
        assert "something went wrong" in str(err)

    def test_ai_error_is_subclass_of_contracts_base(self) -> None:
        from lexigram.ai.exceptions import AIError
        from lexigram.contracts.ai.exceptions import AIError as ContractsAIError
        from lexigram.contracts.exceptions import LexigramError

        assert issubclass(AIError, ContractsAIError)
        assert issubclass(AIError, LexigramError)

    def test_ai_error_has_error_code(self) -> None:
        from lexigram.ai.exceptions import AIError

        assert AIError._code == "LEX_ERR_AI_005"

    def test_ai_error_can_be_raised_and_caught(self) -> None:
        from lexigram.ai.exceptions import AIError
        from lexigram.contracts.exceptions import LexigramError

        with pytest.raises(LexigramError):
            raise AIError("test error")
