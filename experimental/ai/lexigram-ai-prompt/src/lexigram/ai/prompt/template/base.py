"""Abstract base class for all prompt templates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AbstractPromptTemplate(ABC):
    """Common interface for all prompt template implementations.

    Subclasses must implement :meth:`render` and expose :attr:`name`.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this template (used by the registry)."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version of the template (e.g. '1.0.0')."""

    @abstractmethod
    def render(self, **kwargs: Any) -> str | list[dict[str, str]]:
        """Render the template given *kwargs* variable values.

        Returns:
            A plain string (StringPromptTemplate) or a list of chat
            message dicts ``[{"role": ..., "content": ...}, ...]``
            (ChatPromptTemplate).
        """

    @abstractmethod
    def validate(self) -> None:
        """Validate that the template declares all the variables it uses.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptValidationError`:
                If the template string contains variables not declared in the template object.
        """

    def get_variables(self) -> list[str]:
        """Return declared variable names for this template.

        The base implementation returns an empty list; subclasses override
        this to report their declared :class:`~lexigram.ai.prompt.variables.types.PromptVariable` names.
        """
        return []


__all__ = ["AbstractPromptTemplate"]
