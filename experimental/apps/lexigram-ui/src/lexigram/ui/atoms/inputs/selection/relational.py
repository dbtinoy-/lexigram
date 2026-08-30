from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.inputs.base import AbstractInput
from lexigram.ui.atoms.inputs.selection.select import Select
from lexigram.ui.core.base import el


class BelongsTo(Select):
    """Select field for BelongsTo relationships.

    Links to another resource. When ``searchable`` is enabled and an
    ``options_url`` is provided, a filter input is rendered above the select;
    typing loads matching options from the endpoint over HTMX
    (``hx-get`` → ``<option>`` markup swapped into the select).
    """

    def __init__(
        self,
        name: str,
        resource: str,
        searchable: bool = False,
        options_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.resource = resource
        self.searchable = searchable
        self.options_url = options_url

    def _render_input(self) -> Any:
        select_el = super()._render_input()
        if self.searchable:
            select_el.attrs["data-searchable"] = "true"
            select_el.attrs["data-resource"] = self.resource
        if not self.options_url:
            return select_el

        select_id = f"{self.name}-select"
        select_el.attrs["id"] = select_id
        filter_input = el(
            "input",
            type="search",
            name="q",
            placeholder="Search…",
            autocomplete="off",
            class_=(
                "w-full bg-background border border-border rounded-md px-3 py-2 "
                "text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            ),
            **{
                "hx-get": self.options_url,
                "hx-trigger": "keyup changed delay:300ms",
                "hx-target": f"#{select_id}",
                "hx-swap": "innerHTML",
                "hx-include": "this",
            },
        )
        return el("div", filter_input, select_el, class_="space-y-2")


class MorphTo(AbstractInput):
    """Polymorphic relationship selector.

    Consisted of two dropdowns: one for the type and one for the ID.
    """

    def __init__(
        self,
        name: str,
        type_name: str,
        types: list[tuple[str, str]],
        options_url: str,
        type_value: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.type_name = type_name
        self.types = types
        self.options_url = options_url
        self.type_value = type_value

    def _render_input(self) -> Any:
        type_select = Select(
            name=self.type_name,
            choices=self.types,
            value=self.type_value,
            label="Type",
            hx_get=self.options_url,
            hx_target=f"#{self.name}_id_wrapper",
            hx_trigger="change",
            hx_swap="innerHTML",
        )

        id_select_placeholder = Select(
            name=self.name,
            choices=[],
            value=self.value,
            label="Record",
            disabled=(not self.type_value and not self.value),
        )

        id_wrapper = el(
            "div",
            id_select_placeholder,
            id=f"{self.name}_id_wrapper",
            class_="flex-1",
        )

        return el(
            "div",
            el("div", type_select, class_="flex-1"),
            id_wrapper,
            class_="flex gap-4 items-end",
        )

    def render(self) -> Any:
        content = self._render_input()

        if not self.label:
            return content

        return el(
            "div",
            el(
                "label",
                self.label,
                class_="block text-sm font-medium text-foreground mb-2",
            ),
            content,
            self._render_error(),
            class_="mb-6",
        )
