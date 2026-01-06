"""Inline table cell editing component.

Renders a cell value that becomes an input field when clicked.
Saves automatically on blur or Enter, cancels on Escape.
Uses HTMX PATCH to update the record without a full page reload.

Usage::

    InlineEditCell(
        value="Alice",
        resource_url="/admin/users/42",
        field_name="name",
        cell_type="text",
    )
"""

from __future__ import annotations

from typing import Any

from lexigram.ui import Component, el


class InlineEditCell(Component):
    """A table cell whose value can be edited in place.

    On click the cell switches to an ``<input>`` (or ``<select>`` / ``<textarea>``).
    On blur / Enter it fires ``PATCH {resource_url}`` with ``{field_name}=<new_value>``.
    On Escape it discards the change and reverts.

    Args:
        value: Current display value.
        resource_url: URL to PATCH, e.g. ``"/admin/users/42"``.
        field_name: Form field name to send in the PATCH body.
        cell_type: ``"text"``, ``"number"``, ``"select"``, or ``"textarea"``.
        options: For ``cell_type="select"`` — list of ``{"value": …, "label": …}`` dicts.
        placeholder: Placeholder text for the input.
        css_class: Additional Tailwind classes on the outer container.
        editable: When ``False`` renders a plain non-editable cell.
    """

    def __init__(
        self,
        value: str,
        resource_url: str,
        field_name: str,
        *,
        cell_type: str = "text",
        options: list[dict[str, str]] | None = None,
        placeholder: str = "",
        css_class: str = "",
        editable: bool = True,
    ) -> None:
        super().__init__()
        self.value = value
        self.resource_url = resource_url
        self.field_name = field_name
        self.cell_type = cell_type
        self.options = options or []
        self.placeholder = placeholder
        self.css_class = css_class
        self.editable = editable

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _input_el(self) -> Any:
        """Return the el() element for the editable input."""
        base_cls = "w-full px-2 py-1 text-sm rounded border border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-700 dark:text-white"
        escape_js = "if(event.key==='Escape'){this.closest('[data-inline-cell]').querySelector('[data-display]').classList.remove('hidden');this.closest('[data-inline-cell]').querySelector('[data-edit]').classList.add('hidden');}"
        common: dict[str, Any] = {
            "name": self.field_name,
            "class": base_cls,
            "hx-patch": self.resource_url,
            "hx-target": "closest [data-inline-cell]",
            "hx-swap": "outerHTML",
            "onkeydown": escape_js,
        }

        if self.cell_type == "select":
            opts = [
                el(
                    "option",
                    o["label"],
                    value=o["value"],
                    **{"selected": "true"} if o["value"] == self.value else {},
                )
                for o in self.options
            ]
            return el("select", *opts, **{**common, "hx-trigger": "change"})

        if self.cell_type == "textarea":
            return el(
                "textarea",
                self.value,
                rows="2",
                placeholder=self.placeholder,
                **{**common, "hx-trigger": "blur"},
            )

        input_type = "number" if self.cell_type == "number" else "text"
        return el(
            "input",
            type=input_type,
            value=self.value,
            placeholder=self.placeholder,
            **{**common, "hx-trigger": "blur, keyup[key=='Enter']"},
        )

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self) -> object:
        """Render the inline-edit cell wrapper."""
        if not self.editable:
            return el(
                "span",
                self.value,
                class_=f"text-sm text-gray-700 dark:text-gray-300 {self.css_class}".strip(),
            )

        display_el = el(
            "span",
            self.value or "—",
            **{
                "data-display": "true",
                "class": "cursor-pointer text-sm text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 hover:underline",
                "onclick": "this.closest('[data-inline-cell]').querySelector('[data-display]').classList.add('hidden');this.closest('[data-inline-cell]').querySelector('[data-edit]').classList.remove('hidden');this.closest('[data-inline-cell]').querySelector('input,select,textarea').focus();",
            },
        )
        edit_el = el(
            "span",
            self._input_el(),
            **{
                "data-edit": "true",
                "class": "hidden",
            },
        )
        return el(
            "span",
            display_el,
            edit_el,
            **{
                "data-inline-cell": "true",
                "class": f"inline-flex items-center min-w-0 w-full {self.css_class}".strip(),
            },
        )


__all__ = ["InlineEditCell"]
