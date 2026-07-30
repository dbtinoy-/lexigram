"""ChatPromptTemplate — multi-turn conversation template with typed variables."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.prompt.rendering.engine import PromptRenderer, RenderFormat
from lexigram.ai.prompt.template.base import AbstractPromptTemplate
from lexigram.ai.prompt.variables.validators import resolve_variables

if TYPE_CHECKING:
    from lexigram.ai.prompt.variables.types import PromptVariable


class ChatPromptTemplate(AbstractPromptTemplate):
    """A prompt template that produces a list of chat messages.

    Each message slot (``system``, ``user``, ``assistant``) is an optional
    template string.  At render time all provided slots are substituted and
    assembled into the standard ``[{"role": ..., "content": ...}]`` format
    expected by most LLM clients.

    Args:
        name: Unique template name.
        system: Optional system message template string.
        user: Optional user message template string.
        assistant: Optional assistant (prefill) message template string.
        variables: Declared typed variables shared across all slots.
        format: Rendering format.  Defaults to
                :attr:`~lexigram.ai.prompt.rendering.engine.RenderFormat.F_STRING`.
        max_variable_length: Global maximum variable value length in
                characters.  ``0`` means unlimited.
        description: Optional human-readable description.

    Example::

        support = ChatPromptTemplate(
            name="support-agent-v2",
            system="You are a {role} for {company}.",
            user="{customer_query}",
            variables=[
                PromptVariable("role", default="support agent"),
                PromptVariable("company", required=True),
                PromptVariable("customer_query", required=True),
            ],
        )
        messages = support.render(company="Acme Corp", customer_query="Help!")
        # [
        #   {"role": "system", "content": "You are a support agent for Acme Corp."},
        #   {"role": "user",   "content": "Help!"},
        # ]
    """

    def __init__(
        self,
        name: str,
        system: str | None = None,
        user: str | None = None,
        assistant: str | None = None,
        variables: list[PromptVariable] | None = None,
        format: RenderFormat = RenderFormat.F_STRING,
        max_variable_length: int = 0,
        description: str = "",
        version: str = "1.0.0",
    ) -> None:
        self._name = name
        self._system = system
        self._user = user
        self._assistant = assistant
        self._variables: list[PromptVariable] = variables or []
        self._renderer = PromptRenderer(format)
        self._max_variable_length = max_variable_length
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
        for t in [self._system, self._user, self._assistant]:
            if t is not None:
                used_vars.update(self._renderer.get_variables(t))

        declared_vars = set(self.get_variables())
        missing = [v for v in used_vars if v not in declared_vars]
        if missing:
            raise PromptValidationError(
                f"Template '{self._name}' uses undeclared variables: {missing}"
            )

    def get_variables(self) -> list[str]:
        return [v.name for v in self._variables]

    def render(self, **kwargs: Any) -> list[dict[str, str]]:
        """Render all message slots and return a message list.

        Args:
            **kwargs: Variable name → value pairs.

        Returns:
            List of ``{"role": ..., "content": ...}`` dicts.  Only slots
            that were specified at construction time are included.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`:
                A required variable is missing.
            :class:`~lexigram.ai.prompt.exceptions.PromptValidationError`:
                A variable value fails its constraint.
        """
        resolved = resolve_variables(
            self._variables,
            kwargs,
            max_variable_length=self._max_variable_length,
        )
        messages: list[dict[str, str]] = []

        for role, template in [
            ("system", self._system),
            ("user", self._user),
            ("assistant", self._assistant),
        ]:
            if template is not None:
                messages.append(
                    {"role": role, "content": self._renderer.render(template, resolved)}
                )

        return messages

    def render_as_string(self, separator: str = "\n\n", **kwargs: Any) -> str:
        """Render all messages and join them into a single string.

        Args:
            separator: String placed between consecutive messages.
            **kwargs: Variable name → value pairs.

        Returns:
            Single concatenated string of all rendered messages.
        """
        messages = self.render(**kwargs)
        return separator.join(f"[{m['role'].upper()}] {m['content']}" for m in messages)

    def add_message(
        self,
        role: str,
        content: str,
    ) -> ChatPromptTemplate:
        """Return a new template with an additional message appended.

        The new slot uses the *same* variable declarations and rendering
        format as the original.  The new ``role`` must be ``"system"``,
        ``"user"``, or ``"assistant"``.

        Args:
            role: Message role.
            content: Template string for the new message.

        Returns:
            A new :class:`ChatPromptTemplate`.
        """
        valid_roles = {"system", "user", "assistant"}
        if role not in valid_roles:
            raise ValueError(f"role must be one of {valid_roles!r}, got {role!r}.")

        return ChatPromptTemplate(
            name=self._name,
            system=content if role == "system" else self._system,
            user=content if role == "user" else self._user,
            assistant=content if role == "assistant" else self._assistant,
            variables=list(self._variables),
            format=self._renderer.format,
            max_variable_length=self._max_variable_length,
            description=self.description,
            version=self._version,
        )

    def __repr__(self) -> str:  # pragma: no cover
        slots = [
            r
            for r, t in [
                ("system", self._system),
                ("user", self._user),
                ("assistant", self._assistant),
            ]
            if t
        ]
        return f"ChatPromptTemplate(name={self._name!r}, slots={slots!r})"


__all__ = ["ChatPromptTemplate"]
