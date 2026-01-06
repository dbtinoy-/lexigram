"""Prompt Template contracts for Lexigram.

Defines prompt template classes analogous to LangChain's.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass(frozen=True)
class PromptTemplate:
    """A prompt template (like LangChain's PromptTemplate).

    Formats a prompt with variables.
    """

    template: str
    input_variables: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.input_variables:
            object.__setattr__(self, "input_variables", self._extract_variables())

    def _extract_variables(self) -> list[str]:
        """Extract variable names from template."""
        pattern = r"\{(\w+)\}"
        return re.findall(pattern, self.template)

    def format(self, **kwargs: Any) -> str:
        """Format the template with provided variables.

        Args:
            **kwargs: Variable values.

        Returns:
            Formatted prompt string.
        """
        return self.template.format(**kwargs)


@dataclass(frozen=True)
class ChatMessage:
    """A chat message."""

    role: str
    content: str


@dataclass(frozen=True)
class ChatPromptTemplate:
    """Chat prompt template (like LangChain's ChatPromptTemplate).

    Formats chat messages with variables.
    """

    messages: list[tuple[str, str]] = field(default_factory=list)

    @classmethod
    def from_messages(
        cls,
        messages: list[tuple[str, str]],
    ) -> ChatPromptTemplate:
        """Create from a list of message templates."""
        return cls(messages=messages)

    def format(self, **kwargs: Any) -> ChatPromptTemplate:
        """Format the messages with provided variables.

        Args:
            **kwargs: Variable values.

        Returns:
            Formatted ChatPromptTemplate.
        """
        formatted_messages = []
        for role, content in self.messages:
            formatted_content = content.format(**kwargs)
            formatted_messages.append(ChatMessage(role=role, content=formatted_content))

        return ChatPromptTemplate(
            messages=[(m.role, m.content) for m in formatted_messages],
        )


__all__ = [
    "ChatMessage",
    "ChatPromptTemplate",
    "PromptTemplate",
]
