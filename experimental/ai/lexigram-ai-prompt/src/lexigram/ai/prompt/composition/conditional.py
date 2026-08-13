"""ConditionalPrompt — select a template at render time based on a predicate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.prompt.exceptions import PromptNotFoundError
from lexigram.ai.prompt.template.base import AbstractPromptTemplate

if TYPE_CHECKING:
    from collections.abc import Callable


class ConditionalPrompt(AbstractPromptTemplate):
    """Selects one of several templates based on a condition function.

    The first condition that returns ``True`` wins; if no condition matches
    the *default* template is used (if provided), otherwise
    :class:`~lexigram.ai.prompt.exceptions.PromptNotFoundError` is raised.

    Args:
        name: Unique template name.
        branches: Sequence of ``(condition, template)`` pairs.  The
                  *condition* receives the render ``**kwargs`` and returns
                  a bool.
        default: Fallback template used when no condition matches.

    Example::

        prompt = ConditionalPrompt(
            name="tone-selector",
            branches=[
                (lambda **kw: kw.get("formal"), formal_template),
                (lambda **kw: kw.get("casual"), casual_template),
            ],
            default=neutral_template,
        )
        result = prompt.render(formal=True, topic="AI")
    """

    def __init__(
        self,
        name: str,
        branches: list[tuple[Callable[..., bool], AbstractPromptTemplate]],
        default: AbstractPromptTemplate | None = None,
        version: str = "1.0.0",
    ) -> None:
        self._name = name
        self._branches = list(branches)
        self._default = default
        self._version = version

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    def validate(self) -> None:
        """Validate all nested templates."""
        for _, tmpl in self._branches:
            tmpl.validate()
        if self._default:
            self._default.validate()

    def get_variables(self) -> list[str]:
        """Return the union of all branch variable names."""
        seen: dict[str, None] = {}
        for _, tmpl in self._branches:
            for var in tmpl.get_variables():
                seen[var] = None
        if self._default:
            for var in self._default.get_variables():
                seen[var] = None
        return list(seen)

    def render(self, **kwargs: Any) -> str | list[dict[str, str]]:
        """Evaluate conditions in order and render the first matching template.

        Args:
            **kwargs: Variable context forwarded to both the condition and
                      the selected template.

        Returns:
            Rendered output of the winning template.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptNotFoundError`:
                No condition matched and no *default* was provided.
        """
        for condition, template in self._branches:
            if condition(**kwargs):
                return template.render(**kwargs)

        if self._default is not None:
            return self._default.render(**kwargs)

        raise PromptNotFoundError(
            f"ConditionalPrompt '{self._name}': no condition matched and no "
            "default template was provided."
        )

    def __repr__(self) -> str:  # pragma: no cover
        branches = [t.name for _, t in self._branches]
        default = self._default.name if self._default else None
        return (
            f"ConditionalPrompt(name={self._name!r}, "
            f"branches={branches!r}, default={default!r})"
        )


__all__ = ["ConditionalPrompt"]
