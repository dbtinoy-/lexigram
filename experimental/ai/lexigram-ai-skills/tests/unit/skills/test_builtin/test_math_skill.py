"""Tests for MathSkill."""

from __future__ import annotations

import pytest

from lexigram.ai.skills.builtin.math_skill import MathSkill, safe_eval
from lexigram.ai.skills.exceptions import SkillExecutionError


class TestSafeEval:
    """Unit tests for the safe_eval helper."""

    def test_addition(self) -> None:
        assert safe_eval("2 + 3") == 5.0

    def test_subtraction(self) -> None:
        assert safe_eval("10 - 4") == 6.0

    def test_multiplication(self) -> None:
        assert safe_eval("3 * 7") == 21.0

    def test_division(self) -> None:
        assert safe_eval("10 / 4") == 2.5

    def test_floor_division(self) -> None:
        assert safe_eval("10 // 3") == 3.0

    def test_modulo(self) -> None:
        assert safe_eval("10 % 3") == 1.0

    def test_power(self) -> None:
        assert safe_eval("2 ** 10") == 1024.0

    def test_nested_expression(self) -> None:
        assert safe_eval("(2 + 3) * (4 - 1)") == 15.0

    def test_unary_negative(self) -> None:
        assert safe_eval("-5") == -5.0

    def test_raises_on_name_reference(self) -> None:
        with pytest.raises((ValueError, SyntaxError)):
            safe_eval("__import__('os')")

    def test_raises_on_call(self) -> None:
        with pytest.raises(ValueError):
            safe_eval("abs(-1)")

    def test_raises_on_division_by_zero(self) -> None:
        with pytest.raises(ZeroDivisionError):
            safe_eval("1 / 0")

    def test_raises_on_string_literal(self) -> None:
        with pytest.raises(TypeError):
            safe_eval("'hello'")


class TestMathSkill:
    """Tests for the math_calculate built-in skill."""

    @pytest.mark.asyncio
    async def test_valid_expression_returns_ok(self) -> None:
        skill = MathSkill()
        result = await skill.execute(expression="2 ** 10")
        assert result.is_ok()
        output = result.unwrap().output
        assert output["result"] == 1024.0
        assert output["expression"] == "2 ** 10"

    @pytest.mark.asyncio
    async def test_invalid_expression_returns_err(self) -> None:
        skill = MathSkill()
        result = await skill.execute(expression="import os")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SkillExecutionError)

    @pytest.mark.asyncio
    async def test_division_by_zero_returns_err(self) -> None:
        skill = MathSkill()
        result = await skill.execute(expression="1 / 0")
        assert result.is_err()

    def test_definition_name(self) -> None:
        assert MathSkill().definition.name == "math_calculate"
