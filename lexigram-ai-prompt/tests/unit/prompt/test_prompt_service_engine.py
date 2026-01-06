"""Tests for PromptService engine routing (format vs jinja2).

Covers LEX-015: native Jinja2 support in PromptService.
"""

from __future__ import annotations

import pytest

from lexigram.ai.prompt.exceptions import PromptConfigError, PromptRenderError
from lexigram.ai.prompt.service.models import LLMProvider, PromptTemplate
from lexigram.ai.prompt.service.service import PromptService
from lexigram.ai.prompt.service.loader import DictPromptLoader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(*templates: PromptTemplate) -> PromptService:
    return PromptService(list(templates))


def _format_tmpl(content: str, **kwargs: object) -> PromptTemplate:
    return PromptTemplate(
        name="t",
        version="v1",
        content=content,
        engine="format",
        **kwargs,  # type: ignore[arg-type]
    )


def _jinja2_tmpl(content: str, **kwargs: object) -> PromptTemplate:
    return PromptTemplate(
        name="t",
        version="v1",
        content=content,
        engine="jinja2",
        **kwargs,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# format engine (default) — no behaviour change for existing templates
# ---------------------------------------------------------------------------


def test_format_engine_simple_substitution() -> None:
    svc = _make_service(_format_tmpl("Hello, {name}!", required_variables=("name",)))
    from lexigram.ai.prompt.service.models import PromptRenderRequest

    result = svc.render(PromptRenderRequest(name="t", variables={"name": "Alice"}))
    assert result.rendered == "Hello, Alice!"


def test_format_engine_missing_variable_raises() -> None:
    svc = _make_service(_format_tmpl("{x}", required_variables=("x",)))
    from lexigram.ai.prompt.service.models import PromptRenderRequest

    with pytest.raises(PromptRenderError):
        svc.render(PromptRenderRequest(name="t", variables={}))


def test_format_engine_is_default() -> None:
    """engine='format' is the default — existing templates are unaffected."""
    tmpl = PromptTemplate(name="t", version="v1", content="{x}")
    assert tmpl.engine == "format"


# ---------------------------------------------------------------------------
# jinja2 engine — simple variable
# ---------------------------------------------------------------------------


def test_jinja2_engine_simple_variable() -> None:
    pytest.importorskip("jinja2")
    svc = _make_service(_jinja2_tmpl("Hello, {{ name }}!", required_variables=("name",)))
    from lexigram.ai.prompt.service.models import PromptRenderRequest

    result = svc.render(PromptRenderRequest(name="t", variables={"name": "Carol"}))
    assert result.rendered == "Hello, Carol!"


# ---------------------------------------------------------------------------
# jinja2 engine — loop
# ---------------------------------------------------------------------------


def test_jinja2_engine_loop() -> None:
    pytest.importorskip("jinja2")
    content = "{% for item in items %}{{ item }},{% endfor %}"
    svc = _make_service(_jinja2_tmpl(content, required_variables=("items",)))
    from lexigram.ai.prompt.service.models import PromptRenderRequest

    result = svc.render(PromptRenderRequest(name="t", variables={"items": ["a", "b", "c"]}))
    assert result.rendered == "a,b,c,"


# ---------------------------------------------------------------------------
# jinja2 engine — filter
# ---------------------------------------------------------------------------


def test_jinja2_engine_filter() -> None:
    pytest.importorskip("jinja2")
    svc = _make_service(_jinja2_tmpl("{{ name | upper }}", required_variables=("name",)))
    from lexigram.ai.prompt.service.models import PromptRenderRequest

    result = svc.render(PromptRenderRequest(name="t", variables={"name": "lexigram"}))
    assert result.rendered == "LEXIGRAM"


# ---------------------------------------------------------------------------
# engine annotation is honoured: format-engine does NOT execute Jinja2 syntax
# ---------------------------------------------------------------------------


def test_format_engine_does_not_execute_jinja2_syntax() -> None:
    """A format-engine template with {{ }} syntax does not execute Jinja2.

    Python's str.format_map treats {{ and }} as escaped braces, collapsing them
    to literal { and }.  The Jinja2 expression is therefore never evaluated —
    the output is a literal brace-wrapped string, not a rendered Jinja2 value.
    """
    svc = _make_service(_format_tmpl("Value: {{ x }}"))
    from lexigram.ai.prompt.service.models import PromptRenderRequest

    # format_map collapses {{ → { and }} → }, so Jinja2 is never invoked
    result = svc.render(PromptRenderRequest(name="t", variables={}))
    assert result.rendered == "Value: { x }"


# ---------------------------------------------------------------------------
# Unknown engine raises PromptConfigError
# ---------------------------------------------------------------------------


def test_unknown_engine_raises_config_error() -> None:
    """Constructing a PromptTemplate with an unsupported engine value and
    rendering it should raise PromptConfigError."""
    # We bypass the Literal type check with object.__setattr__ because the
    # frozen dataclass stores whatever is given — the guard is at render time.
    tmpl = PromptTemplate(name="t", version="v1", content="x")
    object.__setattr__(tmpl, "engine", "mako")  # unsupported engine

    svc = _make_service(tmpl)
    from lexigram.ai.prompt.service.models import PromptRenderRequest

    with pytest.raises(PromptConfigError, match="unknown engine"):
        svc.render(PromptRenderRequest(name="t", variables={}))


# ---------------------------------------------------------------------------
# Loader: engine field parsed from dict/YAML
# ---------------------------------------------------------------------------


def test_dict_loader_parses_engine_jinja2() -> None:
    loader = DictPromptLoader([
        {
            "name": "tmpl",
            "version": "v1",
            "content": "{{ greeting }}",
            "engine": "jinja2",
        }
    ])
    templates = loader.load()
    assert templates[0].engine == "jinja2"


def test_dict_loader_defaults_engine_to_format() -> None:
    loader = DictPromptLoader([
        {
            "name": "tmpl",
            "version": "v1",
            "content": "{greeting}",
        }
    ])
    templates = loader.load()
    assert templates[0].engine == "format"


def test_dict_loader_rejects_unknown_engine() -> None:
    loader = DictPromptLoader([
        {
            "name": "tmpl",
            "version": "v1",
            "content": "x",
            "engine": "mako",
        }
    ])
    with pytest.raises(ValueError, match="Unknown template engine"):
        loader.load()
