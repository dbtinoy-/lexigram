from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.icons import get_icon
from lexigram.ui.core.base import Component, el


class Toggle(Component):
    """Switch-like toggle component for forms.

    Renders a labeled switch with the same structure used by `Switch` atom but
    centralizes classes and props for consistency.
    """

    def __init__(
        self,
        name: str,
        checked: bool = False,
        label: str | None = None,
        size: str = "md",
        **props,
    ) -> None:
        super().__init__(name=name, checked=checked, label=label, size=size, **props)
        self.name = name
        self.checked = checked
        self.label = label
        self.size = size
        self.props = props

    def render(self) -> Any:
        knob_cls = "inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
        wrapper_cls = "relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"

        return el(
            "div",
            el(
                "div",
                el(
                    "div",
                    el(
                        "span",
                        self.label or "",
                        class_="text-sm font-medium text-foreground",
                        id=f"{self.name}-label",
                    ),
                    el(
                        "button",
                        el(
                            "span",
                            aria_hidden="true",
                            class_=knob_cls,
                            x_bind__class="enabled ? 'translate-x-5' : 'translate-x-0'",
                        ),
                        type="button",
                        role="switch",
                        aria_checked=str(self.checked).lower(),
                        aria_labelledby=f"{self.name}-label",
                        x_data=f"{{ enabled: {'true' if self.checked else 'false'} }}",
                        x_on_click="enabled = !enabled; $refs.hiddenInput.checked = enabled",
                        x_bind__class="enabled ? 'bg-primary' : 'bg-input'",
                        class_=wrapper_cls,
                        **self.props,
                    ),
                    class_="flex-grow flex flex-col",
                ),
                # Hidden input for form submission
                el(
                    "input",
                    type="checkbox",
                    name=self.name,
                    x_ref="hiddenInput",
                    checked=self.checked,
                    class_="hidden",
                ),
                class_="flex items-center justify-between",
            ),
            class_="mb-4",
        )


class ToggleIcon(Component):
    """Icon-based toggle button useful for theme toggles.

    Args:
        icon_on: icon name to show when state var is true
        icon_off: icon name to show when state var is false
        state_var: the JS state variable in scope to toggle (e.g., 'darkMode')
        aria_label: accessible label
    """

    def __init__(
        self,
        icon_on: str = "sun",
        icon_off: str = "moon",
        state_var: str = "darkMode",
        aria_label: str = "Toggle",
        size: str = "sm",
        **props,
    ) -> None:
        super().__init__(
            icon_on=icon_on,
            icon_off=icon_off,
            state_var=state_var,
            aria_label=aria_label,
            size=size,
            **props,
        )
        self.icon_on = icon_on
        self.icon_off = icon_off
        self.state_var = state_var
        self.aria_label = aria_label
        self.size = size
        self.props = props

    def render(self) -> Any:
        icon_size = "w-5 h-5" if self.size == "sm" else "w-6 h-6"
        on_icon = get_icon(self.icon_on, size=icon_size)
        off_icon = get_icon(self.icon_off, size=icon_size)

        return el(
            "button",
            el("span", on_icon, x_show=f"{self.state_var}", class_="text-warning", aria_hidden="true"),
            el(
                "span",
                off_icon,
                x_show=f"!{self.state_var}",
                class_="text-muted-foreground",
                aria_hidden="true",
            ),
            class_="p-2 rounded-lg hover:bg-accent transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            **{"x-on:click": f"{self.state_var} = !{self.state_var}"},
            aria_label=self.aria_label,
            **self.props,
        )
