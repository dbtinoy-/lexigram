from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.icons import get_icon
from lexigram.ui.core.base import Component


class Icon(Component):
    """Icon atom that wraps `get_icon` for consistent usage in templates.

    Args:
        name: icon name (string or raw node)
        size: Tailwind size classes for icon (default: 'w-5 h-5')
        class_name: extra classes to apply to the icon
        aria_hidden: When True (default), marks icon as decorative with aria-hidden="true".
            Set to False for meaningful icons and supply an aria_label.
        aria_label: Accessible label for meaningful icons (used when aria_hidden=False).
    """

    def __init__(
        self,
        name: str | Any,
        size: str = "w-5 h-5",
        class_name: str = "",
        aria_hidden: bool = True,
        aria_label: str | None = None,
        **props,
    ) -> None:
        super().__init__(name=name, size=size, class_name=class_name, **props)
        self.name = name
        self.size = size
        self.class_name = class_name
        self.aria_hidden = aria_hidden
        self.aria_label = aria_label
        self.props = props

    def render(self) -> Any:
        extra: dict[str, Any] = {}
        if self.aria_hidden:
            extra["aria_hidden"] = "true"
        elif self.aria_label is not None:
            extra["aria_label"] = self.aria_label

        return get_icon(
            self.name,
            class_name=self.class_name,
            size=self.size,
            **extra,
            **self.props,
        )
