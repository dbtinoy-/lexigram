from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.inputs.base import AbstractInput
from lexigram.ui.core.base import el


class TextInput(AbstractInput):
    """
    Text input with label and error support.

    Args:
        name: Input name attribute
        value: Input value
        type: Input type (text, password, email, etc.)
        placeholder: Placeholder text
        label: Optional label text
        error: Error message to display
        disabled: Whether input is disabled
        required: Whether input is required
        readonly: Whether input is readonly
        **props: Additional HTML attributes (hx_*, data-*, etc.)

    Example:
        TextInput(
            name="username",
            label="Username",
            placeholder="Enter username",
            required=True
        )
    """

    def __init__(
        self,
        name: str,
        value: str | None = None,
        input_type: str = "text",
        placeholder: str | None = None,
        **kwargs,
    ):
        super().__init__(name=name, value=value, **kwargs)
        self.type = input_type
        self.placeholder = placeholder

    def _render_input(self) -> Any:
        return el(
            "input",
            type=self.type,
            name=self.name,
            id=self.input_id,
            value=self.value or "",
            placeholder=self.placeholder,
            disabled=self.disabled,
            required=self.required,
            readonly=self.readonly,
            class_=self._get_input_classes(),
            **self._get_extra_props(["placeholder", "type"]),
        )


#: Backward-compatible alias — tests and consumers may import ``Input`` directly.
Input = TextInput


class PasswordInput(TextInput):
    """Password input - TextInput with type='password'."""

    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(name=name, input_type="password", **kwargs)


class EmailInput(TextInput):
    """Email input - TextInput with type='email'."""

    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(name=name, input_type="email", **kwargs)


# Merge TextArea here instead of separate file
class TextArea(AbstractInput):
    """
    Multi-line text input.

    Args:
        name: Input name attribute
        value: Input value
        rows: Number of visible rows (default: 3)
        label: Optional label text
        error: Error message to display
        **kwargs: Additional props
    """

    def __init__(
        self,
        name: str,
        value: str | None = None,
        rows: int = 3,
        placeholder: str | None = None,
        **kwargs,
    ):
        super().__init__(name=name, value=value, **kwargs)
        self.rows = rows
        self.placeholder = placeholder

    def _render_input(self) -> Any:
        # Textarea needs a larger minimum height
        classes = self._get_input_classes().replace("h-10", "min-h-[80px]")

        return el(
            "textarea",
            self.value or "",
            name=self.name,
            id=self.input_id,
            rows=self.rows,
            placeholder=self.placeholder,
            disabled=self.disabled,
            required=self.required,
            readonly=self.readonly,
            class_=classes,
            **self._get_extra_props(["placeholder", "rows"]),
        )
