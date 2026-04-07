from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.admin.schema.base import SchemaField
from lexigram.admin.schema.exceptions import FieldError
from lexigram.result import Err, Ok, Result
from lexigram.serialization import dumps_str, loads_str
from lexigram.ui import Element, raw


@dataclass(frozen=True, kw_only=True)
class RepeaterField(SchemaField[list[dict[str, Any]]]):
    """A repeatable group of sub-fields.

    Renders an Alpine.js-managed list of sub-forms, each containing
    the configured ``fields``. Useful for managing ordered or
    nested collections (e.g., line items, social links, addresses).

    Each item is serialised as a JSON object. The whole collection
    is stored as a JSON array.
    """

    fields: list[SchemaField[Any]] = field(default_factory=list)
    min_items: int = 0
    max_items: int | None = None
    add_button_label: str = "Add Item"

    def render_form(
        self, value: list[dict[str, Any]] | None, *, errors: list[str] | None = None
    ) -> Element:
        items = value if value is not None else []

        initial_json = dumps_str(items)
        state_id = f"repeater_{self.name}"

        x_data = (
            f"{{"
            f"  items: {initial_json},"
            f"  addItem() {{"
            f"    if(this.maxItems && this.items.length >= this.maxItems) return;"
            f"    let blank = {{}};"
            f"    this.items.push(blank);"
            f"  }},"
            f"  removeItem(index) {{ this.items.splice(index, 1); }},"
            f"  moveItem(from, to) {{"
            f"    let arr = this.items;"
            f"    let [removed] = arr.splice(from, 1);"
            f"    arr.splice(to, 0, removed);"
            f"  }},"
            f"  get serialized() {{ return JSON.stringify(this.items); }},"
            f"  maxItems: {self.max_items or 'null'},"
            f"}}"
        )

        item_rows: list[Element] = []
        for i, item in enumerate(items):
            sub_fields = self._render_item(item, i)
            item_rows.append(sub_fields)

        template_item = self._build_item_template()

        add_disabled = self.max_items is not None and len(items) >= self.max_items
        add_button = Element(
            "button",
            self.add_button_label,
            type="button",
            **{"@click": "addItem()"},
            disabled="disabled" if add_disabled else None,
            class_=(
                "mt-3 inline-flex items-center px-3 py-1.5 text-xs font-medium "
                "text-primary-600 bg-primary-50 dark:bg-primary-900/30 "
                "dark:text-primary-400 rounded-lg "
                "hover:bg-primary-100 transition-colors duration-200"
            ),
        )

        hidden = Element(
            "input",
            type="hidden",
            name=self.name,
            **{":value": "serialized"},
        )

        counter = (
            Element(
                "p",
                **{"x-text": "`${items.length} item(s)`"},
                class_="text-xs text-gray-500 dark:text-gray-400 mt-1",
            )
            if self.max_items is not None
            else ""
        )

        if self.label:
            return Element(
                "div",
                Element(
                    "label",
                    self.label,
                    class_="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2",
                ),
                Element(
                    "div",
                    template_item,
                    *item_rows,
                    add_button,
                    hidden,
                    counter,
                    **{"x-data": x_data},
                    class_="space-y-3",
                ),
                (
                    Element(
                        "p",
                        errors[0],
                        id=f"{self.name}-error",
                        class_="mt-2 text-sm text-red-600",
                    )
                    if errors
                    else ""
                ),
                class_="mb-6",
            )

        return Element(
            "div",
            template_item,
            *item_rows,
            add_button,
            hidden,
            counter,
            **{"x-data": x_data},
            class_="space-y-3",
        )

    def _render_item(self, item: dict[str, Any], index: int) -> Element:
        rows: list[Element] = []
        for subfield in self.fields:
            sub_value = item.get(subfield.name)
            sub_rendered = subfield.render_form(sub_value)
            rows.append(sub_rendered)

        svg = raw(
            '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" '
            'stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" '
            'stroke-width="2" d="M6 18L18 6M6 6l12 12" />'
            "</svg>"
        )
        remove_btn = Element(
            "button",
            svg,
            type="button",
            **{"@click": f"removeItem({index})"},
            class_=(
                "absolute top-2 right-2 p-1 text-gray-400 hover:text-red-500 "
                "transition-colors duration-200 rounded"
            ),
        )

        return Element(
            "div",
            *rows,
            remove_btn,
            class_="relative p-4 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-900",
        )

    def _build_item_template(self) -> Element:
        tpl_rows: list[Element] = []
        for subfield in self.fields:
            sub_rendered = subfield.render_form(None)
            tpl_rows.append(sub_rendered)

        tpl_svg = raw(
            '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" '
            'stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" '
            'stroke-width="2" d="M6 18L18 6M6 6l12 12" />'
            "</svg>"
        )
        tpl_remove = Element(
            "button",
            tpl_svg,
            type="button",
            **{"@click": "removeItem(index)"},
            class_=(
                '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" '
                'stroke="currentColor">'
                '<path stroke-linecap="round" stroke-linejoin="round" '
                'stroke-width="2" d="M6 18L18 6M6 6l12 12" />'
                "</svg>"
            ),
        )

        tpl = Element(
            "div",
            *tpl_rows,
            tpl_remove,
            class_=(
                "relative p-4 border border-gray-200 dark:border-gray-700 "
                "rounded-xl bg-white dark:bg-gray-900"
            ),
        )

        return Element(
            "template",
            tpl,
            **{"x-for": "(item, index) in items", ":key": "index"},
        )

    def render_column(self, record: Any, value: list[dict[str, Any]] | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        count = len(value)
        label = "item" if count == 1 else "items"
        return Element(
            "span",
            f"{count} {label}",
            class_="text-sm text-gray-600 dark:text-gray-400",
        )

    def from_form(
        self, raw: str | None
    ) -> Result[list[dict[str, Any]] | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Invalid JSON array"))
        try:
            parsed = loads_str(stripped)
        except ValueError:
            return Err(FieldError("Invalid JSON array"))
        if not isinstance(parsed, list):
            return Err(FieldError("Must be a JSON array"))
        validated: list[dict[str, Any]] = []
        for i, item in enumerate(parsed):
            if not isinstance(item, dict):
                return Err(FieldError(f"Item {i} must be a JSON object"))
            validated_item: dict[str, Any] = {}
            for subfield in self.fields:
                sub_raw = item.get(subfield.name)
                sub_value_raw_str = None if sub_raw is None else str(sub_raw)
                sub_result = subfield.from_form(sub_value_raw_str)
                if sub_result.is_err():
                    return Err(
                        FieldError(
                            f"Item {i}.{subfield.name}: {sub_result.unwrap_err()}"
                        )
                    )
                validated_item[subfield.name] = sub_result.unwrap()
            validated.append(validated_item)
        return Ok(validated)

    def to_form(self, value: list[dict[str, Any]] | None) -> str:
        return "" if value is None else dumps_str(value)
