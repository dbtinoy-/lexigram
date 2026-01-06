"""StringPromptTemplate — renders a single string with typed variable substitution."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.prompt.rendering.engine import PromptRenderer, RenderFormat
from lexigram.ai.prompt.template.base import AbstractPromptTemplate
from lexigram.ai.prompt.variables.validators import resolve_variables

if TYPE_CHECKING:
    from lexigram.ai.prompt.variables.types import PromptVariable


class StringPromptTemplate(AbstractPromptTemplate):
    """A single-string prompt template with typed variable validation.

    Supports all :class:`~lexigram.ai.prompt.rendering.engine.RenderFormat`
    modes (f-string by default).

    Args:
        name: Unique template name.
        template: Raw template string, e.g. ``"Hello, {name}!"``.
        variables: Declared :class:`~lexigram.ai.prompt.variables.types.PromptVariable`
                   objects.  Any undeclared variable is passed through as-is.
        format: Rendering format.  Defaults to
                :attr:`~lexigram.ai.prompt.rendering.engine.RenderFormat.F_STRING`.
        description: Optional human-readable description.

    Example::

        tmpl = StringPromptTemplate(
            name="greeting",
            template="Hello, {name}! You are a {role}.",
            variables=[
                PromptVariable("name", required=True),
                PromptVariable("role", default="user"),
            ],
        )
        result = tmpl.render(name="Alice")
        # "Hello, Alice! You are a user."
    """

    def __init__(
        self,
        name: str,
        template: str,
        variables: list[PromptVariable] | None = None,
        format: RenderFormat = RenderFormat.F_STRING,
        description: str = "",
        version: str = "1.0.0",
    ) -> None:
        self._name = name
        self._template = template
        self._variables: list[PromptVariable] = variables or []
        self._renderer = PromptRenderer(format)
        self.description = description
        self._version = version

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    def validate(self) -> None:
        """Validate that all variables used in the template are declared."""
        from lexigram.ai.prompt.exceptions import PromptValidationError

        used_vars = self._renderer.get_variables(self._template)
        declared_vars = set(self.get_variables())
        missing = [v for v in used_vars if v not in declared_vars]
        if missing:
            raise PromptValidationError(
                f"Template '{self._name}' uses undeclared variables: {missing}"
            )

    @property
    def template(self) -> str:
        """The raw (un-rendered) template string."""
        return self._template

    def get_variables(self) -> list[str]:
        return [v.name for v in self._variables]

    def render(self, **kwargs: Any) -> str:
        """Render the template string.

        Args:
            **kwargs: Variable name → value pairs.

        Returns:
            The rendered string.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`:
                A required variable is missing.
            :class:`~lexigram.ai.prompt.exceptions.PromptValidationError`:
                A variable value fails its constraint.
        """
        resolved = resolve_variables(self._variables, kwargs)
        return self._renderer.render(self._template, resolved)

    def partial(self, **kwargs: Any) -> StringPromptTemplate:
        """Return a new template with *kwargs* pre-filled.

        The returned template has the same declared variables; pre-filled
        ones will override missing values at render time.

        Args:
            **kwargs: Variables to pre-fill.

        Returns:
            A new :class:`StringPromptTemplate` with a partial closure.
        """
        outer = self

        class _PartialStringTemplate(StringPromptTemplate):
            def render(self, **inner_kwargs: Any) -> str:
                merged = {**kwargs, **inner_kwargs}
                return outer.render(**merged)

        return _PartialStringTemplate(
            name=f"{self._name}__partial",
            template=self._template,
            variables=self._variables,
            format=self._renderer.format,
            description=self.description,
            version=self._version,
        )

    def __add__(self, other: StringPromptTemplate) -> StringPromptTemplate:
        """Concatenate two templates with a newline separator.

        The resulting template inherits the format of ``self``.
        """
        if not isinstance(other, StringPromptTemplate):
            raise TypeError(
                f"Cannot concatenate StringPromptTemplate with {type(other).__name__}."
            )
        merged_vars = list(self._variables)
        existing_names = {v.name for v in merged_vars}
        for v in other._variables:
            if v.name not in existing_names:
                merged_vars.append(v)

        return StringPromptTemplate(
            name=f"{self._name}+{other._name}",
            template=f"{self._template}\n{other._template}",
            variables=merged_vars,
            format=self._renderer.format,
            version=self._version,
        )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"StringPromptTemplate(name={self._name!r}, "
            f"format={self._renderer.format.value!r})"
        )


__all__ = ["StringPromptTemplate"]
