"""
Base input component with shared functionality.
All input types should inherit from this class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from lexigram.ui.core.base import Component, el


class AbstractInput(ABC, Component):
    """
    Abstract base for all input components.

    Provides:
    - Common props handling (name, value, label, error, disabled, required)
    - Shared CSS class generation
    - Common wrapper rendering (label + error display)

    Subclasses must implement:
    - _render_input(): Returns the actual input element
    """

    # Shared CSS classes - defined once, used everywhere
    BASE_CLASSES = (
        "flex h-10 w-full rounded-md border border-input bg-background "
        "px-3 py-2 text-base ring-offset-background "
        "file:border-0 file:bg-transparent file:text-sm file:font-medium "
        "placeholder:text-muted-foreground "
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring "
        "focus-visible:ring-offset-2 "
        "disabled:cursor-not-allowed disabled:opacity-50"
    )

    ERROR_CLASSES = "border-destructive focus:border-destructive focus:ring-destructive"
    NORMAL_CLASSES = ""
    READONLY_CLASSES = "bg-muted opacity-80"

    LABEL_CLASSES = "block text-sm font-medium leading-6 text-foreground"
    ERROR_MSG_CLASSES = "mt-1 text-xs text-destructive min-h-[1.25rem]"
    HELP_TEXT_CLASSES = "mt-1 text-xs text-muted-foreground"
    WRAPPER_CLASSES = "flex flex-col gap-1.5 w-full"

    def __init__(
        self,
        name: str,
        value: Any = None,
        label: str | None = None,
        error: str | Sequence[str] | None = None,
        help_text: str | None = None,
        disabled: bool = False,
        required: bool = False,
        readonly: bool = False,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.name = name
        self.value = value
        self.label = label
        self.error = error
        self.help_text = help_text
        self.disabled = disabled
        self.required = required
        self.readonly = readonly

    @property
    def _error_messages(self) -> list[str]:
        """Normalize ``error`` to a list of messages."""
        if not self.error:
            return []
        if isinstance(self.error, str):
            return [self.error]
        return [str(m) for m in self.error if m]

    @property
    def input_id(self) -> str:
        """Get the input ID (from props or fallback to name)."""
        return self.props.get("id") or self.name

    def _get_input_classes(self, extra_classes: str = "") -> str:
        """
        Generate complete CSS class string for input element.

        Handles:
        - Base styling
        - Error state
        - Readonly state
        - Custom width classes
        - Additional classes from props
        """
        custom = self.props.get("class_", "")

        # Don't add w-full if custom width is specified
        has_custom_width = any(w in custom for w in ["w-", "max-w-", "min-w-"])

        parts = [
            self.BASE_CLASSES,
            "" if has_custom_width else "w-full",
            self.ERROR_CLASSES if self.error else self.NORMAL_CLASSES,
            self.READONLY_CLASSES if self.readonly else "",
            extra_classes,
            custom,
        ]

        return " ".join(filter(None, parts))

    def _get_extra_props(self, exclude: list[str] | None = None) -> dict:
        """
        Extract non-standard props for passthrough to element.

        Filters out standard input props and returns the rest
        (useful for hx_* attributes, data-* attributes, etc.)
        """
        standard_props = {
            "name",
            "value",
            "label",
            "error",
            "help_text",
            "disabled",
            "required",
            "readonly",
            "class_",
            "class",
            "id",
            *(exclude or []),
        }
        extra = {k: v for k, v in self.props.items() if k not in standard_props}
        # Wire accessibility attributes automatically so every input shares
        # the same error/help semantics: aria-invalid on validation failure
        # and aria-describedby pointing at the help/error messages.
        if self._error_messages:
            extra["aria-invalid"] = "true"
        described_by = self._described_by
        if described_by:
            extra["aria-describedby"] = " ".join(described_by)
        return extra

    @property
    def _described_by(self) -> list[str]:
        """IDs referenced by ``aria-describedby`` (help + validation messages)."""
        ids: list[str] = []
        if self.help_text and not self.error:
            ids.append(f"{self.input_id}-help")
        if self._error_messages:
            for index, _message in enumerate(self._error_messages):
                ids.append(
                    f"{self.input_id}-error"
                    if index == 0
                    else f"{self.input_id}-error-{index + 1}"
                )
        return ids

    def _render_label(self) -> Any:
        """Render label element if label text is provided."""
        if not self.label:
            return None

        return el(
            "label",
            self.label,
            for_=self.input_id,
            class_=self.LABEL_CLASSES,
        )

    def _render_error(self) -> Any:
        """Render the first validation message (legacy single-error callers)."""
        errors = self._render_errors()
        return errors[0] if errors else None

    def _render_errors(self) -> list[Any]:
        """Render one ``<p>`` per validation message (if any)."""
        messages = self._error_messages
        error_id = f"{self.input_id}-error"
        if len(messages) == 1:
            return [
                el(
                    "p",
                    messages[0],
                    id=error_id,
                    role="alert",
                    class_=self.ERROR_MSG_CLASSES,
                )
            ]
        return [
            el(
                "p",
                message,
                id=error_id if index == 0 else f"{error_id}-{index + 1}",
                role="alert",
                class_=self.ERROR_MSG_CLASSES,
            )
            for index, message in enumerate(messages)
        ]

    def _render_help(self) -> Any:
        """Render help text after the input (hidden when an error is shown)."""
        if not self.help_text or self.error:
            return None
        return el(
            "p",
            self.help_text,
            id=f"{self.input_id}-help",
            class_=self.HELP_TEXT_CLASSES,
        )

    def _render_with_wrapper(self, input_el: Any) -> Any:
        """
        Wrap input with label, help text and error messages.

        If no decoration is needed, returns just the input element.
        """
        label = self._render_label()
        help_text = self._render_help()
        errors = self._render_errors()

        if label is None and help_text is None and not errors:
            return input_el

        children: list[Any] = [label] if label is not None else []
        children.append(input_el)
        if help_text is not None:
            children.append(help_text)
        children.extend(errors)

        return el("div", *children, class_=self.WRAPPER_CLASSES)

    @abstractmethod
    def _render_input(self) -> Any:
        """
        Render the actual input element.

        Subclasses MUST implement this method.
        Should return the raw input element without wrapper.
        """
        ...

    def render(self) -> Any:
        """
        Render complete input component.

        Calls _render_input() and wraps with label/error if needed.
        """
        return self._render_with_wrapper(self._render_input())
