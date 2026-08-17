"""PromptPipeline — chains templates sequentially, feeding output into the next."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.prompt.exceptions import PromptRenderError

if TYPE_CHECKING:
    from lexigram.ai.prompt.template.base import AbstractPromptTemplate


class PromptPipeline:
    """Chains a sequence of :class:`~lexigram.ai.prompt.template.base.AbstractPromptTemplate` objects.

    Each template's rendered output is injected into the *next* template's
    context under the key specified by *output_key* (default ``"input"``).
    The initial call provides the variables for the first template; subsequent
    templates receive ``output_key=<previous output>`` merged with the same
    ``**kwargs``.

    Args:
        templates: Ordered sequence of templates to chain.
        output_key: The variable name under which each stage's output is
                    passed to the following stage.  Defaults to ``"input"``.

    Raises:
        ValueError: Fewer than two templates are provided.

    Example::

        pipeline = PromptPipeline(
            templates=[topic_template, elaboration_template],
            output_key="previous",
        )
        final = pipeline.run(subject="climate change")
    """

    def __init__(
        self,
        templates: list[AbstractPromptTemplate],
        output_key: str = "input",
    ) -> None:
        if len(templates) < 1:
            raise ValueError("PromptPipeline requires at least one template.")
        self._templates = list(templates)
        self._output_key = output_key

    @property
    def templates(self) -> list[AbstractPromptTemplate]:
        """The ordered list of templates in this pipeline."""
        return list(self._templates)

    def run(self, **kwargs: Any) -> str | list[dict[str, str]]:
        """Execute the pipeline and return the final template's output.

        Args:
            **kwargs: Initial variable context passed to the first template and
                      available to all subsequent templates (merged with the
                      intermediate output at each step).

        Returns:
            The rendered output of the last template in the chain.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`:
                Any template in the chain fails to render.
        """
        context: dict[str, Any] = dict(kwargs)
        result: str | list[dict[str, str]] | None = None

        for i, template in enumerate(self._templates):
            try:
                result = template.render(**context)
            except Exception as exc:  # template engine can raise any exception; re-raised as PromptRenderError
                raise PromptRenderError(
                    f"Pipeline stage {i} ('{template.name}') failed: {exc}"
                ) from exc

            # Feed string output into the next stage; list output is skipped.
            if isinstance(result, str):
                context = {**context, self._output_key: result}

        return result  # type: ignore[return-value]

    def __repr__(self) -> str:  # pragma: no cover
        names = [t.name for t in self._templates]
        return f"PromptPipeline(stages={names!r})"


__all__ = ["PromptPipeline"]
