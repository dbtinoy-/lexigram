from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class Switch(Component):
    """
    A premium toggle switch component implemented using the shared `Toggle` molecule.
    """

    def __init__(
        self,
        label: str,
        name: str,
        value: bool = False,
        description: str | None = None,
        error: str | None = None,
        **props,
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

        # Delegate to Toggle molecule for consistent rendering
        t = Toggle(name=self.name, checked=self.value, label=self.label, **self.props)

        # Append error node if present
        base = t.render()
        if self.error:
            return el(
                "div",
                base,
                el("p", self.error, class_="mt-2 text-sm text-destructive", role="alert"),
                class_="mb-4",
            )
        return base
