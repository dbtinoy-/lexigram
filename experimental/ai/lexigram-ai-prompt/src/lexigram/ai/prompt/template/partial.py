"""PartialPromptTemplate — wraps any template with pre-filled variable values."""

from __future__ import annotations

from typing import Any

from lexigram.ai.prompt.template.base import AbstractPromptTemplate


class PartialPromptTemplate(AbstractPromptTemplate):
    """Wraps any :class:`~lexigram.ai.prompt.template.base.AbstractPromptTemplate`
    and pre-fills a subset of its variables.

    The pre-filled values can be overridden at render time by passing the
    same key in ``render(**kwargs)``.

    Args:
        template: Underlying template to wrap.
        partial_variables: Variable name → pre-filled value mapping.

    Example::

        base = StringPromptTemplate(
            name="email",
            template="Dear {recipient},\\n\\n{body}\\n\\nRegards, {sender}",
            variables=[
                PromptVariable("recipient", required=True),
                PromptVariable("body", required=True),
                PromptVariable("sender", required=True),
            ],
        )
        support_email = PartialPromptTemplate(base, sender="Support Team")
        result = support_email.render(recipient="Alice", body="How can we help?")
    """

    def __init__(
        self,
        template: AbstractPromptTemplate,
        **partial_variables: Any,
    ) -> None:
        self._template = template
        self._partial: dict[str, Any] = dict(partial_variables)

    @property
    def name(self) -> str:
        return f"{self._template.name}__partial"

    @property
    def version(self) -> str:
        return self._template.version

    def validate(self) -> None:
        """Validate the underlying template."""
        self._template.validate()

    def get_variables(self) -> list[str]:
        return self._template.get_variables()

    def render(self, **kwargs: Any) -> str | list[dict[str, str]]:
        """Render by merging pre-filled values with *kwargs*.

        Pre-filled values act as defaults; *kwargs* take precedence.
        """
        merged = {**self._partial, **kwargs}
        return self._template.render(**merged)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"PartialPromptTemplate(template={self._template.name!r}, "
            f"partial_keys={list(self._partial)!r})"
        )


__all__ = ["PartialPromptTemplate"]
