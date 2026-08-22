"""Tests for template construction and validation."""

from __future__ import annotations

import pytest

from lexigram.ai.prompt.exceptions import PromptValidationError

from prompt_lab.repository.templates import TEMPLATES


class TestTemplates:
    def test_v1_declares_variables_and_renders(self) -> None:
        tpl = TEMPLATES["v1"]()

        assert set(tpl.get_variables()) == {"issue", "tone"}
        rendered = tpl.render(issue="late parcel", tone="neutral")
        text = str(rendered)
        assert "late parcel" in text

    def test_v2_includes_examples(self) -> None:
        tpl = TEMPLATES["v2"]()
        text = str(tpl.render(issue="late parcel", tone="warm"))
        assert "happy to help" in text.lower()

    def test_undeclared_variable_fails_validation(self) -> None:
        from lexigram.ai.prompt.template.chat import ChatPromptTemplate

        bad = ChatPromptTemplate(
            "bad", user="Hello {undeclared}", variables=[],
        )
        with pytest.raises(PromptValidationError):
            bad.validate()

    def test_variant_labels(self) -> None:
        assert set(TEMPLATES) == {"v1", "v2"}
