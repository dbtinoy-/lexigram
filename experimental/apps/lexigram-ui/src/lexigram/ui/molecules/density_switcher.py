"""Density switcher for DataTable rows.

Renders a compact segmented control offering the three supported row
densities (``compact``, ``normal``, ``comfortable``) and emits HTMX
requests carrying the chosen ``density`` query param through the
updated :class:`TableState`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ui import Component, HTMXAttrs, Zones, el

if TYPE_CHECKING:
    from lexigram.ui.state import TableState

_DENSITY_OPTIONS: tuple[tuple[str, str, str], ...] = (
    ("compact", "rows-4", "Compact rows"),
    ("normal", "rows-3", "Normal rows"),
    ("comfortable", "rows-2", "Comfortable rows"),
)


class DensitySwitcher(Component):
    """Density switcher (compact | normal | comfortable) for DataTable.

    Density is presentation-only: switching never resets pagination and
    the choice round-trips through the URL so it is per-user and
    shareable. The active option renders as a pressed toggle with HTMX
    navigation disabled; inactive options request a full table refresh
    with the new ``density`` state.

    Args:
        current: Active density (``"compact"``, ``"normal"`` or
            ``"comfortable"``).
        resource_prefix: Resource URL prefix for HTMX requests.
        state: Optional :class:`TableState` used to build the updated
            state (and therefore the request URL).
        **props: Additional element properties.
    """

    def __init__(
        self,
        current: str = "normal",
        resource_prefix: str | None = None,
        state: TableState | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.current = (
            current if current in ("compact", "normal", "comfortable") else "normal"
        )
        self.resource_prefix = resource_prefix or ""
        self.state = state

    def _button_props(
        self,
        type_name: str,
        icon_name: str,
        label: str,
    ) -> dict[str, Any]:
        """Build the props for one density option button."""
        is_active = self.current == type_name

        props: dict[str, Any] = {
            "label": "",
            "icon": icon_name,
            "variant": "ghost",
            "size": "sm",
            "title": label,
            "aria_label": label,
            "aria-pressed": "true" if is_active else "false",
        }

        if is_active:
            props["class_"] = (
                "bg-muted text-primary-600 dark:text-primary-400 "
                "cursor-default pointer-events-none"
            )
        else:
            if self.state:
                updated_state = self.state.with_density(
                    type_name,  # type: ignore[arg-type]
                )
                htmx_attrs = HTMXAttrs.for_full_refresh(
                    updated_state,
                    self.resource_prefix,
                    push_url=True,
                )
                for key, val in htmx_attrs.items():
                    props[key.replace("-", "_")] = val
            else:
                props.update(
                    {
                        "hx_get": (
                            f"{self.resource_prefix.rstrip('/')}/?density={type_name}"
                        ),
                        "hx_target": Zones.TABLE.selector,
                        "hx_swap": "outerHTML",
                        "hx_params": "none",
                        "hx_push_url": "true",
                    },
                )

            props.update(
                {
                    "hx_on": f"click:console.log('density:{type_name}')",
                    "class_": (
                        "text-muted-foreground hover:text-foreground hover:bg-muted "
                        "dark:text-muted-foreground dark:hover:text-foreground "
                        "dark:hover:bg-card"
                    ),
                },
            )

        return props

    def render(self) -> Any:
        from lexigram.ui import ActionButton

        buttons = [
            ActionButton(**self._button_props(value, icon, label))
            for value, icon, label in _DENSITY_OPTIONS
        ]

        return el(
            "div",
            el(
                "div",
                *[btn.render() for btn in buttons],
                class_=(
                    "inline-flex items-center gap-1 bg-card rounded-md "
                    "p-1 border border-border"
                ),
            ),
            # Hidden on small screens, visible on md+ (desktop only)
            class_="density-switcher hidden md:inline-flex items-center gap-2 text-sm",
        )


__all__ = ["DensitySwitcher"]
