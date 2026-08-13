"""Tests for PromptPipeline and ConditionalPrompt."""

from __future__ import annotations

import pytest

from lexigram.ai.prompt.composition.conditional import ConditionalPrompt
from lexigram.ai.prompt.composition.pipeline import PromptPipeline
from lexigram.ai.prompt.exceptions import PromptNotFoundError, PromptRenderError
from lexigram.ai.prompt.template.string import StringPromptTemplate
from lexigram.ai.prompt.variables.types import PromptVariable


def _tmpl(name: str, template: str, **var_kwargs: object) -> StringPromptTemplate:
    return StringPromptTemplate(name=name, template=template)


# ---------------------------------------------------------------------------
# PromptPipeline
# ---------------------------------------------------------------------------


def test_pipeline_single_template() -> None:
    t = StringPromptTemplate(name="a", template="Hello {name}!")
    pipeline = PromptPipeline(templates=[t])
    assert pipeline.run(name="World") == "Hello World!"


def test_pipeline_two_stages() -> None:
    t1 = StringPromptTemplate(name="a", template="Hello {name}!")
    # t2 gets output of t1 injected as 'input'
    t2 = StringPromptTemplate(name="b", template="Preview: {input}")
    pipeline = PromptPipeline(templates=[t1, t2], output_key="input")
    result = pipeline.run(name="Alice")
    assert result == "Preview: Hello Alice!"


def test_pipeline_three_stages() -> None:
    t1 = StringPromptTemplate(name="a", template="{x} step1")
    t2 = StringPromptTemplate(name="b", template="{input} step2")
    t3 = StringPromptTemplate(name="c", template="{input} step3")
    pipeline = PromptPipeline(templates=[t1, t2, t3])
    result = pipeline.run(x="start")
    assert result == "start step1 step2 step3"


def test_pipeline_empty_raises() -> None:
    with pytest.raises(ValueError, match="at least one"):
        PromptPipeline(templates=[])


def test_pipeline_run_raises_on_stage_failure() -> None:
    from lexigram.ai.prompt.variables.types import PromptVariable

    t1 = StringPromptTemplate(
        name="failing",
        template="{required_var}",
        variables=[PromptVariable("required_var", required=True)],
    )
    pipeline = PromptPipeline(templates=[t1])
    with pytest.raises(PromptRenderError, match="failing"):
        pipeline.run()  # missing required_var


def test_pipeline_templates_property() -> None:
    t = _tmpl("a", "x")
    pipeline = PromptPipeline(templates=[t])
    assert pipeline.templates == [t]


# ---------------------------------------------------------------------------
# ConditionalPrompt
# ---------------------------------------------------------------------------


def test_conditional_first_branch_wins() -> None:
    formal = StringPromptTemplate(name="formal", template="Good day, {name}.")
    casual = StringPromptTemplate(name="casual", template="Hey {name}!")
    prompt = ConditionalPrompt(
        name="tone",
        branches=[
            (lambda **kw: kw.get("formal", False), formal),
            (lambda **kw: True, casual),
        ],
    )
    result = prompt.render(name="Alice", formal=True)
    assert result == "Good day, Alice."


def test_conditional_falls_through_to_second() -> None:
    formal = StringPromptTemplate(name="formal", template="Good day, {name}.")
    casual = StringPromptTemplate(name="casual", template="Hey {name}!")
    prompt = ConditionalPrompt(
        name="tone",
        branches=[
            (lambda **kw: kw.get("formal", False), formal),
            (lambda **kw: True, casual),
        ],
    )
    result = prompt.render(name="Bob")
    assert result == "Hey Bob!"


def test_conditional_uses_default() -> None:
    fallback = StringPromptTemplate(name="fallback", template="Default {msg}.")
    prompt = ConditionalPrompt(
        name="p",
        branches=[
            (lambda **kw: False, StringPromptTemplate(name="never", template="nope")),
        ],
        default=fallback,
    )
    result = prompt.render(msg="here")
    assert result == "Default here."


def test_conditional_no_match_no_default_raises() -> None:
    prompt = ConditionalPrompt(
        name="p",
        branches=[
            (lambda **kw: False, StringPromptTemplate(name="never", template="nope")),
        ],
    )
    with pytest.raises(PromptNotFoundError, match="no condition matched"):
        prompt.render()


def test_conditional_get_variables_union() -> None:
    t1 = StringPromptTemplate(
        name="a", template="", variables=[PromptVariable("x"), PromptVariable("y")]
    )
    t2 = StringPromptTemplate(
        name="b", template="", variables=[PromptVariable("y"), PromptVariable("z")]
    )
    prompt = ConditionalPrompt(name="p", branches=[(lambda **kw: False, t1), (lambda **kw: False, t2)])
    vars_ = prompt.get_variables()
    assert set(vars_) == {"x", "y", "z"}
