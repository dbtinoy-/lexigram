from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.inputs.base import AbstractInput
from lexigram.ui.core.base import el


class Select(AbstractInput):
    """Select dropdown with label and error support.

    Args:
        name: Input name attribute
        choices: List of (value, label) tuples
        value: Currently selected value
        label: Optional label text
        error: Error message to display
        multiple: Whether multiple selection is allowed
        disabled: Whether input is disabled
        required: Whether input is required
    """

    def __init__(
        self,
        name: str,
        choices: list[tuple[str, str]] | None = None,
        multiple: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.choices = choices or []
        self.multiple = multiple

    def _render_input(self) -> Any:
        options = []
        for val, label in self.choices:
            is_selected = False
            if self.multiple and isinstance(self.value, (list, tuple)):
                is_selected = val in self.value
            else:
                is_selected = str(val) == str(
                    self.value if self.value is not None else "",
                )

            options.append(
                el(
                    "option",
                    label,
                    value=val,
                    selected=is_selected,
                ),
            )

        # Merge HTMX triggers for cascading dropdowns
        extra_props = self._get_extra_props(exclude=["choices", "multiple"])
        depends_on = self.props.get("depends_on")
        options_from = self.props.get("options_from")
        if depends_on and options_from:
            extra_props["hx-get"] = options_from
            extra_props["hx-trigger"] = f"change from:#{depends_on}"
            extra_props["hx-target"] = "this"
            extra_props["hx-swap"] = "innerHTML"
            extra_props["hx-include"] = f"#{depends_on}"

        return el(
            "select",
            *options,
            name=self.name,
            id=self.input_id,
            multiple=self.multiple,
            disabled=self.disabled,
            required=self.required,
            aria_invalid="true" if self.error else None,
            aria_describedby=f"{self.input_id}-error" if self.error else None,
            aria_required="true" if self.required else None,
            aria_disabled="true" if self.disabled else None,
            class_=self._get_input_classes(
                "pl-3 pr-10 h-8 shadow-sm ring-1 ring-inset sm:text-sm leading-5",
            ),
            **extra_props,
        )


class NativeMultiSelect(Select):
    """Native browser multiple select dropdown."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["multiple"] = True
        super().__init__(*args, **kwargs)


class LazySelect(Select):
    """Select dropdown that support infinite scroll / lazy loading of options."""

    def __init__(
        self,
        name: str,
        lazy_url: str,
        choices: list[tuple[str, str]] | None = None,
        page: int = 1,
        **kwargs: Any,
    ) -> None:
        super().__init__(name, choices=choices, **kwargs)
        self.lazy_url = lazy_url
        self.page = page

    def render_options(self) -> list[Any]:
        options = []
        for val, label in self.choices:
            is_selected = str(val) == str(self.value if self.value is not None else "")
            options.append(el("option", label, value=val, selected=is_selected))

        next_page = self.page + 1
        sentinel = el(
            "option",
            "Loading more...",
            value="",
            disabled=True,
            **{
                "hx-get": f"{self.lazy_url}?page={next_page}",
                "hx-trigger": "intersect once",
                "hx-swap": "afterend",
                "hx-indicator": "this",
            },
        )
        options.append(sentinel)
        return options

    def _render_input(self) -> Any:
        if self.props.get("is_fragment"):
            return self.render_options()

        options = self.render_options()

        return el(
            "select",
            *options,
            name=self.name,
            id=self.input_id,
            multiple=self.multiple,
            disabled=self.disabled,
            required=self.required,
            class_=self._get_input_classes(
                "pl-3 pr-10 h-8 shadow-sm ring-1 ring-inset sm:text-sm leading-5",
            ),
            **self._get_extra_props(exclude=["lazy_url", "page", "is_fragment"]),
        )
