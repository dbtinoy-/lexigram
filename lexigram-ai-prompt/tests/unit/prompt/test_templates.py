"""Tests for StringPromptTemplate, ChatPromptTemplate, FewShotPromptTemplate, PartialPromptTemplate."""

from __future__ import annotations

import pytest

from lexigram.ai.prompt.exceptions import PromptRenderError, PromptValidationError
from lexigram.ai.prompt.template.chat import ChatPromptTemplate
from lexigram.ai.prompt.template.few_shot import FewShotPromptTemplate, InMemoryExampleSelector
from lexigram.ai.prompt.template.partial import PartialPromptTemplate
from lexigram.ai.prompt.template.string import StringPromptTemplate
from lexigram.ai.prompt.variables.types import PromptVariable


# ---------------------------------------------------------------------------
# StringPromptTemplate
# ---------------------------------------------------------------------------


def test_string_render_basic() -> None:
    tmpl = StringPromptTemplate(name="hello", template="Hello, {name}!")
    assert tmpl.render(name="World") == "Hello, World!"


def test_string_render_with_declared_variable() -> None:
    tmpl = StringPromptTemplate(
        name="greeting",
        template="Hi {name}, you are {role}.",
        variables=[
            PromptVariable("name", required=True),
            PromptVariable("role", default="user"),
        ],
    )
    assert tmpl.render(name="Alice") == "Hi Alice, you are user."
    assert tmpl.render(name="Bob", role="admin") == "Hi Bob, you are admin."


def test_string_render_missing_required_raises() -> None:
    tmpl = StringPromptTemplate(
        name="t",
        template="{company}",
        variables=[PromptVariable("company", required=True)],
    )
    with pytest.raises(PromptRenderError, match="company"):
        tmpl.render()


def test_string_render_validation_error() -> None:
    tmpl = StringPromptTemplate(
        name="t",
        template="{count}",
        variables=[PromptVariable("count", type=int)],
    )
    with pytest.raises(PromptValidationError):
        tmpl.render(count="not-int")


def test_string_get_variables() -> None:
    tmpl = StringPromptTemplate(
        name="t",
        template="",
        variables=[PromptVariable("a"), PromptVariable("b")],
    )
    assert tmpl.get_variables() == ["a", "b"]


def test_string_partial() -> None:
    tmpl = StringPromptTemplate(
        name="t",
        template="Dear {recipient}, from {sender}.",
        variables=[PromptVariable("recipient", required=True), PromptVariable("sender", required=True)],
    )
    partial_tmpl = tmpl.partial(sender="Support Team")
    result = partial_tmpl.render(recipient="Alice")
    assert result == "Dear Alice, from Support Team."


def test_string_add_concatenates() -> None:
    t1 = StringPromptTemplate(name="a", template="Hello {name}.")
    t2 = StringPromptTemplate(name="b", template="How are you, {name}?")
    combined = t1 + t2
    result = combined.render(name="Alice")
    assert result == "Hello Alice.\nHow are you, Alice?"


def test_string_add_type_error() -> None:
    t = StringPromptTemplate(name="a", template="x")
    with pytest.raises(TypeError):
        t + "not-a-template"  # type: ignore[operator]


# ---------------------------------------------------------------------------
# ChatPromptTemplate
# ---------------------------------------------------------------------------


def test_chat_render_all_slots() -> None:
    tmpl = ChatPromptTemplate(
        name="chat",
        system="You are {role}.",
        user="{query}",
        assistant="Got it.",
        variables=[PromptVariable("role", required=True), PromptVariable("query", required=True)],
    )
    messages = tmpl.render(role="a helper", query="Hello?")
    assert len(messages) == 3
    assert messages[0] == {"role": "system", "content": "You are a helper."}
    assert messages[1] == {"role": "user", "content": "Hello?"}
    assert messages[2] == {"role": "assistant", "content": "Got it."}


def test_chat_render_partial_slots() -> None:
    tmpl = ChatPromptTemplate(name="chat", system="System only.")
    messages = tmpl.render()
    assert len(messages) == 1
    assert messages[0]["role"] == "system"


def test_chat_render_as_string() -> None:
    tmpl = ChatPromptTemplate(name="chat", system="S", user="U")
    result = tmpl.render_as_string()
    assert "[SYSTEM]" in result
    assert "[USER]" in result


def test_chat_add_message() -> None:
    tmpl = ChatPromptTemplate(name="t", system="Hello")
    updated = tmpl.add_message("user", "World")
    messages = updated.render()
    assert len(messages) == 2
    assert messages[1]["role"] == "user"


def test_chat_add_message_invalid_role() -> None:
    tmpl = ChatPromptTemplate(name="t")
    with pytest.raises(ValueError, match="role must be one of"):
        tmpl.add_message("moderator", "...")


def test_chat_get_variables() -> None:
    tmpl = ChatPromptTemplate(
        name="t",
        variables=[PromptVariable("x"), PromptVariable("y")],
    )
    assert tmpl.get_variables() == ["x", "y"]


# ---------------------------------------------------------------------------
# FewShotPromptTemplate
# ---------------------------------------------------------------------------


def test_few_shot_render() -> None:
    selector = InMemoryExampleSelector(
        examples=[{"input": "2+2", "output": "4"}, {"input": "3*3", "output": "9"}],
        k=2,
    )
    tmpl = FewShotPromptTemplate(
        name="math",
        prefix="Solve these:\n",
        suffix="Q: {question}\nA:",
        example_selector=selector,
        variables=[PromptVariable("question", required=True)],
    )
    result = tmpl.render(question="5+5")
    assert "2+2" in result
    assert "3*3" in result
    assert "5+5" in result
    assert result.startswith("Solve these:")


def test_few_shot_k_limits_examples() -> None:
    selector = InMemoryExampleSelector(
        examples=[{"input": str(i), "output": str(i)} for i in range(10)],
        k=2,
    )
    tmpl = FewShotPromptTemplate(
        name="t",
        prefix="",
        suffix="{q}",
        example_selector=selector,
        variables=[PromptVariable("q", required=True)],
    )
    result = tmpl.render(q="?")
    # Only examples 0 and 1 should appear
    assert "0" in result
    assert "1" in result
    assert "2" not in result


def test_inmemory_selector_add() -> None:
    selector = InMemoryExampleSelector(examples=[], k=5)
    selector.add({"input": "a", "output": "b"})
    assert len(selector.select()) == 1


# ---------------------------------------------------------------------------
# PartialPromptTemplate
# ---------------------------------------------------------------------------


def test_partial_pre_fills_variable() -> None:
    base = StringPromptTemplate(
        name="email",
        template="Dear {recipient}, from {sender}.",
        variables=[PromptVariable("recipient", required=True), PromptVariable("sender", required=True)],
    )
    partial = PartialPromptTemplate(base, sender="Support Team")
    assert partial.render(recipient="Alice") == "Dear Alice, from Support Team."


def test_partial_kwargs_override_partial() -> None:
    base = StringPromptTemplate(
        name="t",
        template="{x} {y}",
        variables=[PromptVariable("x", required=True), PromptVariable("y", required=True)],
    )
    partial = PartialPromptTemplate(base, x="default_x")
    assert partial.render(x="override", y="y_val") == "override y_val"


def test_partial_name_format() -> None:
    base = StringPromptTemplate(name="base", template="")
    p = PartialPromptTemplate(base)
    assert p.name == "base__partial"


def test_partial_get_variables_delegates() -> None:
    base = StringPromptTemplate(
        name="t",
        template="",
        variables=[PromptVariable("a"), PromptVariable("b")],
    )
    p = PartialPromptTemplate(base)
    assert p.get_variables() == ["a", "b"]
