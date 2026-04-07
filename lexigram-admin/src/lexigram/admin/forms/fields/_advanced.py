from __future__ import annotations

import copy
from typing import Any

from lexigram.admin.forms.fields._base import Field
import lexigram.serialization as json
from lexigram.ui import ColorPicker, Component, MarkdownEditor, RichEditor, TagsInput
from lexigram.ui import KeyValueField as KeyValueWidget


class RichTextField(Field):
    """WYSIWYG rich-text editor field (backed by Trix)."""

    def render(self, **kwargs) -> Component:
        return RichEditor(
            name=self.name,
            value=self.value,
            label=self.label,
            error=str(self.errors[0]) if self.errors else None,
            required=self.required,
            disabled=self.disabled,
            **kwargs,
        )


class MarkdownField(Field):
    """Markdown editor field with preview."""

    def render(self, **kwargs) -> Component:
        return MarkdownEditor(
            name=self.name,
            value=self.value,
            label=self.label,
            error=str(self.errors[0]) if self.errors else None,
            required=self.required,
            disabled=self.disabled,
            **kwargs,
        )


class ColorField(Field):
    """HTML color-picker field."""

    def render(self, **kwargs) -> Component:
        return ColorPicker(
            name=self.name,
            value=self.value,
            label=self.label,
            error=str(self.errors[0]) if self.errors else None,
            required=self.required,
            disabled=self.disabled,
            **kwargs,
        )


class TagsField(Field):
    """Comma-separated tags / chips field."""

    def render(self, **kwargs) -> Component:
        return TagsInput(
            name=self.name,
            value=self.value,
            label=self.label,
            error=str(self.errors[0]) if self.errors else None,
            required=self.required,
            disabled=self.disabled,
            **kwargs,
        )


class KeyValueField(Field):
    """Dynamic key-value pairs editor (serialises to JSON object)."""

    def render(self, **kwargs) -> Component:
        return KeyValueWidget(
            name=self.name,
            value=self.value,
            label=self.label,
            error=str(self.errors[0]) if self.errors else None,
            required=self.required,
            disabled=self.disabled,
            **kwargs,
        )


class JsonField(Field):
    """JSON document editor with code-formatted textarea.

    Renders a ``<textarea>`` pre-populated with pretty-printed JSON.
    On submit the value is the raw JSON string; the form layer should
    call :meth:`parse_value` to deserialise.

    Args:
        rows: Number of visible textarea rows (default ``10``).
        indent: JSON pretty-print indent level (default ``2``).
    """

    def __init__(
        self,
        label: str = "",
        *,
        rows: int = 10,
        indent: int = 2,
        **kwargs: Any,
    ) -> None:
        super().__init__(label=label, **kwargs)
        self.rows = rows
        self.indent = indent

    def bind(self, value: Any) -> JsonField:
        """Bind a Python object (dict/list) or raw JSON string as the value."""
        new_field = copy.copy(self)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                dumped = json.dumps(parsed)
                new_field.value = (
                    dumped.decode() if isinstance(dumped, bytes) else dumped
                )
            except (ValueError, TypeError):
                new_field.value = value
        elif value is not None:
            dumped = json.dumps(value)
            new_field.value = dumped.decode() if isinstance(dumped, bytes) else dumped
        else:
            new_field.value = ""
        new_field.is_bound = True
        return new_field

    def parse_value(self, raw: str) -> Any:
        """Deserialise the submitted JSON string.

        Returns:
            Parsed Python object.

        Raises:
            ValueError: If *raw* is not valid JSON.
        """
        try:
            return json.loads(raw)
        except ValueError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc

    def render(self, **kwargs) -> Component:
        from lexigram.ui.core.base import el

        textarea_attrs: dict[str, Any] = {
            "name": self.name,
            "id": self.name,
            "rows": str(self.rows),
            "class": (
                "block w-full rounded-md border border-gray-300 dark:border-gray-600 "
                "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 "
                "font-mono text-sm p-3 "
                "focus:outline-none focus:ring-2 focus:ring-blue-500 "
                "disabled:opacity-50"
            ),
            "spellcheck": "false",
        }
        if self.disabled:
            textarea_attrs["disabled"] = True
        if self.required:
            textarea_attrs["required"] = True

        raw = self.value if self.value is not None else ""
        textarea = el("textarea", raw, **textarea_attrs)

        label_el = el(
            "label",
            self.label or self.name,
            **{
                "for": self.name,
                "class": "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1",
            },
        )
        error_el = (
            el("p", str(self.errors[0]), class_="mt-1 text-sm text-red-600")
            if self.errors
            else None
        )
        help_el = (
            el("p", self.help_text, class_="mt-1 text-xs text-gray-500")
            if self.help_text
            else None
        )
        children = [label_el, textarea]
        if error_el:
            children.append(error_el)
        if help_el:
            children.append(help_el)
        return el("div", *children, class_="space-y-1", **kwargs)
