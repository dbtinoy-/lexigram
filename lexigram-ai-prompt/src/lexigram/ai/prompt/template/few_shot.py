"""FewShotPromptTemplate — few-shot examples with pluggable example selection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from lexigram.ai.prompt.rendering.engine import PromptRenderer, RenderFormat
from lexigram.ai.prompt.template.base import AbstractPromptTemplate
from lexigram.ai.prompt.variables.validators import resolve_variables

if TYPE_CHECKING:
    from lexigram.ai.prompt.variables.types import PromptVariable


class ExampleSelectorProtocol(ABC):
    """Protocol for few-shot example selectors.

    Implementations select the most relevant examples for a given query.
    """

    @abstractmethod
    def select(self, **kwargs: Any) -> list[dict[str, str]]:
        """Return selected examples based on render context.

        Args:
            **kwargs: Current render context.

        Returns:
            List of selected example dicts.
        """


class InMemoryExampleSelector(ExampleSelectorProtocol):
    """Simple in-memory example selector.

    Selects the first *k* examples from the provided list by default.
    Subclass and override :meth:`select` for similarity-based selection.

    Args:
        examples: List of example dicts.
        k: Maximum number of examples to include.
    """

    def __init__(self, examples: list[dict[str, str]], k: int = 3) -> None:
        self._examples = list(examples)
        self._k = k

    def select(self, **kwargs: Any) -> list[dict[str, str]]:
        """Return up to *k* examples.

        The base implementation returns the first *k* entries.  Override
        this method to implement query-based or similarity-based selection.

        Args:
            **kwargs: Current render context (unused in base implementation).

        Returns:
            List of selected example dicts.
        """
        return self._examples[: self._k]

    def add(self, example: dict[str, str]) -> None:
        """Append an example to the pool."""
        self._examples.append(example)


class FewShotPromptTemplate(AbstractPromptTemplate):
    """A prompt template that injects few-shot examples before the query.

    Examples are formatted with *example_template* (defaults to
    ``"{input}\\n{output}"``) and injected between the *prefix* and *suffix*
    with *example_separator* as a delimiter.

    Args:
        name: Unique template name.
        prefix: Text shown before all examples.
        suffix: Text shown after all examples (typically contains the actual
                query placeholder, e.g. ``"Q: {question}\\nA:"``).
        example_selector: Provides the examples to inject.
        example_template: Per-example template string.  Must reference the
                          keys present in each example dict.
        example_separator: Delimiter between examples.  Defaults to ``"\\n\\n"``.
        variables: Additional typed variables for the *suffix*.
        format: Rendering format for *prefix*, *suffix*, and *example_template*.
        description: Optional human-readable description.

    Example::

        selector = InMemoryExampleSelector(
            examples=[
                {"input": "2+2", "output": "4"},
                {"input": "3*3", "output": "9"},
            ],
            k=2,
        )
        tmpl = FewShotPromptTemplate(
            name="math-few-shot",
            prefix="Solve the following math problems:\\n",
            suffix="Q: {question}\\nA:",
            example_selector=selector,
            variables=[PromptVariable("question", required=True)],
        )
        print(tmpl.render(question="5+5"))
    """

    def __init__(
        self,
        name: str,
        prefix: str,
        suffix: str,
        example_selector: ExampleSelectorProtocol,
        example_template: str = "{input}\n{output}",
        example_separator: str = "\n\n",
        variables: list[PromptVariable] | None = None,
        format: RenderFormat = RenderFormat.F_STRING,
        description: str = "",
        version: str = "1.0.0",
    ) -> None:
        self._name = name
        self._prefix = prefix
        self._suffix = suffix
        self._selector = example_selector
        self._example_template = example_template
        self._example_separator = example_separator
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

        used_vars: set[str] = set()

        # We only check variables in prefix and suffix since example_template
        # variables come from the example dicts, not the kwargs
        used_vars.update(self._renderer.get_variables(self._prefix))
        used_vars.update(self._renderer.get_variables(self._suffix))

        declared_vars = set(self.get_variables())
        missing = [v for v in used_vars if v not in declared_vars]
        if missing:
            raise PromptValidationError(
                f"Template '{self._name}' uses undeclared variables: {missing}"
            )

    def get_variables(self) -> list[str]:
        return [v.name for v in self._variables]

    def render(self, **kwargs: Any) -> str:
        """Render the few-shot prompt.

        Selects examples, formats each one, then assembles:
        ``prefix + example_separator + examples + example_separator + suffix``.

        Args:
            **kwargs: Variable name → value pairs used in *suffix*.

        Returns:
            Fully rendered prompt string.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`:
                A required variable is missing.
        """
        resolved = resolve_variables(self._variables, kwargs)

        examples = self._selector.select(**kwargs)
        formatted_examples = [
            self._renderer.render(self._example_template, ex) for ex in examples
        ]

        parts = [self._prefix]
        if formatted_examples:
            parts.append(self._example_separator.join(formatted_examples))
        parts.append(self._renderer.render(self._suffix, resolved))
        return self._example_separator.join(parts)


__all__ = [
    "ExampleSelectorProtocol",
    "FewShotPromptTemplate",
    "InMemoryExampleSelector",
]
