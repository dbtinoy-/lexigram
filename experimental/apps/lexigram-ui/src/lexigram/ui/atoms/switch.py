from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component


class Switch(Component):
    """Premium switch that delegates to the shared accessible toggle."""

    def __init__(
        self,
        label: str,
        name: str,
        value: bool = False,
        description: str | None = None,
        error: str | None = None,
        **props: Any,
    ) -> None:
        super().__init__(
            label=label,
            name=name,
            value=value,
            description=description,
            error=error,
            **props,
        )
        self.label = label
        self.name = name
        self.value = value
        self.description = description
        self.error = error
        self.props = props

    def render(self) -> Any:
        from lexigram.ui.molecules.toggle import Toggle

        # Pass the full field contract instead of leaking disabled, required,
        # or error as arbitrary attributes on the visual button.
        props = dict(self.props)
        disabled = bool(props.pop("disabled", False))
        required = bool(props.pop("required", False))
        readonly = bool(props.pop("readonly", False))
        return Toggle(
            name=self.name,
            checked=self.value,
            label=self.label,
            description=self.description,
            error=self.error,
            disabled=disabled,
            required=required,
            readonly=readonly,
            **props,
        ).render()
