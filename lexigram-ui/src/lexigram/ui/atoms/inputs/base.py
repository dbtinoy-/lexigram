"""
Base input component with shared functionality.
All input types should inherit from this class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
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
    WRAPPER_CLASSES = "flex flex-col gap-1.5 w-full"

    def __init__(
        self,
        name: str,
        value: Any = None,
        label: str | None = None,
        error: str | None = None,
        disabled: bool = False,
        required: bool = False,
        readonly: bool = False,
        **props,
    ):
        super().__init__(**props)
        self.name = name
        self.value = value
        self.label = label
        self.error = error
        self.disabled = disabled
        self.required = required
        self.readonly = readonly

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
            "disabled",
            "required",
            "readonly",
            "class_",
            "class",
            "id",
            *(exclude or []),
        }
        return {k: v for k, v in self.props.items() if k not in standard_props}

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
        """Render error message if present."""
        if not self.error:
            return None

        return el(
            "p",
            self.error,
            id=f"{self.input_id}-error",
            role="alert",
            class_=self.ERROR_MSG_CLASSES,
        )

    def _render_with_wrapper(self, input_el: Any) -> Any:
        """
        Wrap input with label and error message.

        If no label is provided, returns just the input element.
        """
        if not self.label:
            return input_el

        return el(
            "div",
            self._render_label(),
            input_el,
            self._render_error(),
            class_=self.WRAPPER_CLASSES,
        )

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
